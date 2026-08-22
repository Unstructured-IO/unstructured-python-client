import re
import tomllib
from pathlib import Path

from unstructured_client.models import shared
from unstructured_client.utils.forms import serialize_multipart_form

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
    assert not any("cryptography" in d for d in project["dependencies"]), (
        "cryptography is unused and must not be a runtime dependency"
    )

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
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "speakeasy_sdk_publish.yaml"
    ).read_text()

    assert "release:" in workflow
    assert "pypa/gh-action-pypi-publish" in workflow
    assert "PYPI_TOKEN" not in workflow
    assert "upload-artifact" in workflow
    assert "download-artifact" in workflow
    assert re.search(r"publish:\n\s+needs: build", workflow)
    assert re.search(
        r"publish:\n(?:.*\n)*?\s+permissions:\n\s+contents: read\n\s+id-token: write",
        workflow,
    )


def test_release_workflow_keeps_oidc_out_of_build_job():
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "speakeasy_sdk_publish.yaml"
    ).read_text()

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
        assert path in genignore, (
            f"{path} carries custom code and must stay in .genignore"
        )

    # The docs row is generated from the spec too, so a regeneration would drop it
    # without the .genignore entry above.
    response_docs = (
        REPO_ROOT / "docs/models/operations/partitionresponse.md"
    ).read_text()
    assert "elements_file" in response_docs


def test_basesdk_keeps_cleaning_the_base_url():
    """`_get_url` is the only point every operation's base URL passes through.

    An operation-level `server_url=` override bypasses the SDK-init hook, so the
    cleaning has to live in this generated file, and the .genignore entry is the only
    thing keeping it through a regeneration. Without it a URL copied from the app
    doubles its /api/v1 prefix again and every Platform call 404s.

    Note: SDK generation is currently blocked at the Speakeasy account level, so this
    guards a path that cannot execute today.
    """
    from unstructured_client import basesdk

    source = (REPO_ROOT / "src/unstructured_client/basesdk.py").read_text()
    assert "clean_server_url(utils.template_url(base_url, url_variables))" in source
    assert basesdk.clean_server_url is not None

    genignore = (REPO_ROOT / ".genignore").read_text()
    assert "src/unstructured_client/basesdk.py" in genignore, (
        "basesdk.py carries custom code and must stay in .genignore"
    )


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
