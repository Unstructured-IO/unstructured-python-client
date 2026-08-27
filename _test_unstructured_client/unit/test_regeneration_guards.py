import inspect
import json
import re

import pytest
from pathlib import Path
import tomllib

from unstructured_client.models import shared
from unstructured_client.types import Unset
from unstructured_client.utils.forms import serialize_multipart_form
from unstructured_client.utils.metadata import MultipartFormMetadata, find_field_metadata


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_pyproject() -> dict:
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())


def test_pyproject_invariants():
    data = _load_pyproject()
    project = data["project"]

    assert project["dynamic"] == ["version"]
    assert "version" not in project
    assert project["requires-python"] == ">=3.11"
    assert "httpcore >=1.0.9" in project["dependencies"]
    assert "pydantic >=2.12.5" in project["dependencies"]
    assert not any("cryptography" in d for d in project["dependencies"]), \
        "cryptography is unused and must not be a runtime dependency"

    dynamic_version = data["tool"]["setuptools"]["dynamic"]["version"]
    assert dynamic_version == {"attr": "unstructured_client._version.__version__"}

    build = data["build-system"]
    assert build["build-backend"] == "setuptools.build_meta"
    assert "setuptools>=80" in build["requires"]


def test_publish_script_is_hardened():
    publish_script = (REPO_ROOT / "scripts" / "publish.sh").read_text()

    assert "set -euo pipefail" in publish_script
    assert "sys.version_info < (3, 11)" in publish_script
    assert "uv build --out-dir dist --clear" in publish_script


def test_release_workflow_uses_trusted_publishing():
    workflow = (REPO_ROOT / ".github" / "workflows" / "speakeasy_sdk_publish.yaml").read_text()

    assert "release:" in workflow
    assert "pypa/gh-action-pypi-publish" in workflow
    assert "PYPI_TOKEN" not in workflow
    assert "upload-artifact" in workflow
    assert "download-artifact" in workflow
    assert re.search(r"publish:\n\s+needs: build", workflow)
    assert re.search(r"publish:\n(?:.*\n)*?\s+permissions:\n\s+contents: read\n\s+id-token: write", workflow)


def test_release_workflow_keeps_oidc_out_of_build_job():
    workflow = (REPO_ROOT / ".github" / "workflows" / "speakeasy_sdk_publish.yaml").read_text()

    build_job = workflow.split("\n  publish:\n", maxsplit=1)[0]

    assert "id-token: write" not in build_job


def test_speakeasy_workflow_does_not_manage_pypi_publishing():
    workflow = (REPO_ROOT / ".speakeasy" / "workflow.yaml").read_text()

    assert "publish:" not in workflow
    assert "PYPI_TOKEN" not in workflow


def test_makefile_installs_with_locked_uv_sync():
    makefile = (REPO_ROOT / "Makefile").read_text()

    assert "uv sync --locked" in makefile


def test_ci_installs_with_locked_uv_sync():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yaml").read_text()

    assert 'UV_LOCKED: "1"' in workflow
    assert "run: make install" in workflow


def test_partition_response_keeps_elements_file():
    """`elements_file` is client-side only, so no spec change can restore it after a regen.

    Both the model and the enum value that selects it live in generated files; the
    .genignore entries are the only thing keeping them.

    Note: SDK generation is currently blocked at the Speakeasy account level, so this
    guards a path that cannot execute today. Whether it is worth keeping is a live
    question -- see the discussion on PR #347.
    """
    from unstructured_client.general import PartitionAcceptEnum
    from unstructured_client.models import operations

    assert "elements_file" in operations.PartitionResponse.model_fields
    assert "elements_file" in operations.PartitionResponseTypedDict.__annotations__
    assert PartitionAcceptEnum.APPLICATION_X_NDJSON.value == "application/x-ndjson"

    genignore = (REPO_ROOT / ".genignore").read_text()
    for path in (
        "src/unstructured_client/general.py",
        "src/unstructured_client/models/operations/partition.py",
        "docs/models/operations/partitionresponse.md",
    ):
        assert path in genignore, f"{path} carries custom code and must stay in .genignore"

    # The docs row is generated from the spec too, so a regeneration would drop it
    # without the .genignore entry above.
    response_docs = (REPO_ROOT / "docs/models/operations/partitionresponse.md").read_text()
    assert "elements_file" in response_docs


def test_body_create_job_input_files_are_serialized_as_multipart_files():
    request = shared.BodyCreateJob(
        request_data="{}",
        input_files=[
            shared.InputFiles(
                content=b"hello",
                file_name="hello.pdf",
                content_type="application/pdf",
            )
        ],
    )

    media_type, form, files = serialize_multipart_form("multipart/form-data", request)

    assert media_type == "multipart/form-data"
    assert form == {"request_data": "{}"}
    assert files == [("input_files[]", ("hello.pdf", b"hello", "application/pdf"))]


def test_body_run_workflow_input_files_are_serialized_as_multipart_files():
    request = shared.BodyRunWorkflow(
        input_files=[
            shared.BodyRunWorkflowInputFiles(
                content=b"hello",
                file_name="hello.pdf",
                content_type="application/pdf",
            )
        ]
    )

    media_type, form, files = serialize_multipart_form("multipart/form-data", request)

    assert media_type == "multipart/form-data"
    assert form == {}
    assert files == [("input_files[]", ("hello.pdf", b"hello", "application/pdf"))]


def test_job_status_enums_stay_forward_tolerant():
    """REJECTED and the `_missing_` hook are hand-written; nothing regenerates them.

    REJECTED is in the live spec, but the `_missing_` hook cannot be: a generated enum is
    closed. Speakeasy generation is decommissioned, so this test - not `.genignore` - is what
    protects both.
    """
    for enum in (shared.JobStatus, shared.JobProcessingStatus):
        assert enum.REJECTED.value == "REJECTED"

        # An unrecognised value is preserved verbatim rather than raising or
        # collapsing to a sentinel.
        unknown = enum("SOME_FUTURE_STATUS")
        assert isinstance(unknown, enum)
        assert unknown.value == "SOME_FUTURE_STATUS"
        # Repeated lookups must return the same object, not grow a new one each time.
        assert unknown is enum("SOME_FUTURE_STATUS")
        # ...and must not leak into the declared member set.
        assert "SOME_FUTURE_STATUS" not in enum.__members__

    for name in ("jobstatus", "jobprocessingstatus"):
        docs = (REPO_ROOT / f"docs/models/shared/{name}.md").read_text()
        assert "REJECTED" in docs


def test_genignore_covers_code_the_spec_cannot_produce():
    """`.genignore` must list every file carrying code no spec can generate.

    The rule is narrow on purpose. `skip_preflight` on the three workflow models IS in the live
    spec, so a regeneration would reproduce it and listing those files would only freeze them
    against future spec-driven fields. These four cannot come from the spec at all:
      - the `_missing_` hook: a generated enum is closed;
      - `BodyCreateJob.skip_preflight` and its fold: `Body_create_job` has no such property,
        because the spec types `request_data` as a plain string;
      - the `Unset` export in `types/__init__.py`: the generator exports the singleton but not
        its type.
    """
    genignore = (REPO_ROOT / ".genignore").read_text()
    for path in (
        "src/unstructured_client/models/shared/jobstatus.py",
        "src/unstructured_client/models/shared/jobprocessingstatus.py",
        "docs/models/shared/jobstatus.md",
        "docs/models/shared/jobprocessingstatus.md",
        "src/unstructured_client/models/shared/body_create_job.py",
        "docs/models/shared/bodycreatejob.md",
        "src/unstructured_client/types/__init__.py",
    ):
        assert path in genignore, f"{path} carries custom code and must stay in .genignore"

    # The converse: files whose custom content IS spec-derivable must NOT be frozen.
    for path in (
        "src/unstructured_client/models/shared/createworkflow.py",
        "src/unstructured_client/models/shared/updateworkflow.py",
        "src/unstructured_client/models/shared/workflowinformation.py",
    ):
        assert path not in genignore, (
            f"{path} should not be in .genignore: skip_preflight is in the live spec, so "
            "freezing the file would only block future spec-driven fields"
        )


def test_workflow_models_expose_skip_preflight():
    """`skip_preflight` is the preflight opt-out; it must stay on all four models.

    It mirrors `reprocess_all` exactly: `OptionalNullable[bool] = UNSET` on the two request
    models so an unset value is omitted rather than sent, and `Optional[bool] = False` on the
    response model so the server's echo is readable.
    """
    for model in (shared.CreateWorkflow, shared.UpdateWorkflow):
        field = model.model_fields["skip_preflight"]
        assert isinstance(field.default, Unset), (
            f"{model.__name__}.skip_preflight must default to UNSET so an unset value is "
            "omitted from the request body, not sent as false"
        )
        # Both lists in serialize_model matter: missing from optional_fields, the serializer's
        # `elif` branch emits the field on every call.
        source = inspect.getsource(model.serialize_model)
        assert source.count('"skip_preflight"') == 2, (
            f"{model.__name__}.serialize_model must list skip_preflight in BOTH "
            "optional_fields and nullable_fields"
        )

    info_field = shared.WorkflowInformation.model_fields["skip_preflight"]
    assert info_field.default is False

    job_field = shared.BodyCreateJob.model_fields["skip_preflight"]
    assert isinstance(job_field.default, Unset)
    # Deliberately carries no multipart metadata: the validator folds it into request_data, and
    # serialize_multipart_form skips any field without MultipartFormMetadata.
    assert find_field_metadata(job_field, MultipartFormMetadata) is None


def test_body_create_job_folds_skip_preflight_into_request_data():
    """Unset must be tested with `isinstance(..., Unset)`, never `is UNSET`.

    Pydantic deep-copies the default per instance, so an identity check against the singleton
    silently fails open and rewrites `request_data` on every call.
    """
    untouched = '{"template_id":"t"}'
    assert shared.BodyCreateJob(request_data=untouched).request_data == untouched

    for value in (True, False):
        body = shared.BodyCreateJob(request_data=untouched, skip_preflight=value)
        assert json.loads(body.request_data) == {"template_id": "t", "skip_preflight": value}


def test_unset_is_publicly_importable():
    """`Unset` must stay exported, or `body_create_job` cannot import it.

    `UNSET` alone is not enough: pydantic deep-copies the default per model instance, so callers
    need the *type* to test for unset-ness rather than an identity check against the singleton.
    Without this export the only route is a private import of `utils.values._is_set` from a
    models module, which crosses a package boundary for an underscore-prefixed name.
    """
    from unstructured_client import types

    assert "Unset" in types.__all__
    assert isinstance(types.UNSET, types.Unset)

    # The property that makes the type necessary in the first place.
    body = shared.BodyCreateJob(request_data="{}")
    assert body.skip_preflight is not types.UNSET
    assert isinstance(body.skip_preflight, types.Unset)


def test_body_create_job_folds_on_assignment_not_only_construction():
    """`skip_preflight` must survive being set after construction.

    The field carries no multipart metadata, so a dropped fold reaches the wire as nothing at
    all and raises nothing - the job would run *with* preflight while the caller believes it is
    off. `validate_assignment=True` on the model is what closes that; the fold writes through
    `__dict__` to avoid re-entering itself.
    """
    body = shared.BodyCreateJob(request_data='{"a":1}')
    assert body.request_data == '{"a":1}', "unset must not rewrite the payload"

    body.skip_preflight = True
    assert json.loads(body.request_data) == {"a": 1, "skip_preflight": True}

    # Toggling back must write false, not leave the previous true in place.
    body.skip_preflight = False
    assert json.loads(body.request_data) == {"a": 1, "skip_preflight": False}

    # Replacing the payload must re-apply the flag rather than lose it.
    body.request_data = '{"z":9}'
    assert json.loads(body.request_data) == {"z": 9, "skip_preflight": False}

    # The base model config must be merged, not replaced.
    assert shared.BodyCreateJob.model_config["populate_by_name"] is True
    assert shared.BodyCreateJob.model_config["validate_assignment"] is True


def test_body_create_job_folds_skip_preflight_through_model_copy():
    """`model_copy(update=...)` bypasses validation, so the fold has to be re-applied.

    The dangerous direction is the second case: a body that already folded `true`, copied with
    `skip_preflight=False`, would keep sending `true` and run the job with preflight disabled
    while the caller believes they just re-enabled it.
    """
    lost = shared.BodyCreateJob(request_data='{"a":1}').model_copy(
        update={"skip_preflight": True}
    )
    assert json.loads(lost.request_data)["skip_preflight"] is True

    reenabled = shared.BodyCreateJob(
        request_data='{"a":1}', skip_preflight=True
    ).model_copy(update={"skip_preflight": False})
    assert json.loads(reenabled.request_data)["skip_preflight"] is False

    # A copy with no update must not change the payload.
    body = shared.BodyCreateJob(request_data='{"a":1}', skip_preflight=True)
    for copied in (body.model_copy(), body.model_copy(deep=True)):
        assert copied.request_data == body.request_data


@pytest.mark.parametrize(
    "request_data",
    [
        '{"x": 0.123456789012345678901}',  # more precision than a float64 can hold
        '{"x": 1e5}',  # exponent form survives
        '{"x": 1E+2}',
        '{"x": 1.50}',  # trailing zero is significant to some consumers
        '{"n": "café"}',  # non-ASCII stays as written
        '{"a":1}',
    ],
)
def test_body_create_job_fold_preserves_the_callers_bytes(request_data):
    """Adding the flag must not re-encode the rest of the payload.

    A json.loads/json.dumps round trip preserves *values* but not their representation, and
    `request_data` carries caller configuration that may reach precision-sensitive consumers.
    The fold splices instead, so every other byte survives verbatim.
    """
    folded = shared.BodyCreateJob(
        request_data=request_data, skip_preflight=True
    ).request_data

    original_body = request_data.strip()[1:-1].strip()
    assert original_body in folded, f"{original_body!r} was rewritten: {folded!r}"
    assert json.loads(folded)["skip_preflight"] is True


@pytest.mark.parametrize("request_data", ["{}", "{ }", '{"a":1}  '])
def test_body_create_job_fold_handles_empty_and_padded_objects(request_data):
    """The splice has to cope with an empty object and with surrounding whitespace."""
    folded = shared.BodyCreateJob(
        request_data=request_data, skip_preflight=True
    ).request_data
    assert json.loads(folded)["skip_preflight"] is True


def test_body_create_job_fold_is_a_no_op_once_correct():
    """Re-running the fold must not touch an already-correct payload.

    `validate_assignment=True` re-runs every model validator on *any* field assignment, so
    without an early return, touching an unrelated field would drive the payload down the
    re-encode branch and silently reformat it - undoing the byte-preservation above.
    """
    body = shared.BodyCreateJob(request_data='{"x": 1e5}', skip_preflight=True)
    folded = body.request_data
    assert "1e5" in folded

    body.input_files = None
    assert body.request_data == folded, "an unrelated assignment reformatted request_data"

    unchanged = body.model_copy(update={"input_files": None})
    assert unchanged.request_data == folded
