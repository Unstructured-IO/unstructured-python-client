"""Behaviour of the hand-maintained `skip_preflight` and job-status model code.

These assert what the models *do*, not how they are protected from regeneration: `.genignore`
was removed from this repo, so a test asserting entries in it would assert nothing. What is
left here is the real cover - if a regeneration (or a careless edit) drops `skip_preflight`,
the fold, or the enums' forward tolerance, these fail.
"""

import inspect
import json
from pathlib import Path

import pytest

from unstructured_client.models import shared
from unstructured_client.types import Unset
from unstructured_client.utils.metadata import MultipartFormMetadata, find_field_metadata


REPO_ROOT = Path(__file__).resolve().parents[2]

def test_job_status_enums_stay_forward_tolerant():
    """REJECTED and the `_missing_` hook are hand-written; nothing regenerates them.

    REJECTED is in the live spec, but the `_missing_` hook cannot be: a generated enum is
    closed. Nothing regenerates this file, so this test is what protects both.
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


@pytest.mark.parametrize("request_data", ["{}", "{ }", '{"a":1}  ', '  {"a":1}'])
def test_body_create_job_fold_handles_empty_and_padded_objects(request_data):
    """The splice has to cope with an empty object and with surrounding whitespace."""
    folded = shared.BodyCreateJob(
        request_data=request_data, skip_preflight=True
    ).request_data
    assert json.loads(folded)["skip_preflight"] is True


@pytest.mark.parametrize(
    "request_data",
    [
        '{\n  "a": 1\n}\n',  # indentation and a trailing newline
        '{\n  "x": 0.123456789012345678901\n}\n',  # ...alongside a number that must not move
        '{"a":1}  ',  # trailing spaces
        '  {"a":1}',  # leading spaces
        "{ }",  # the gap inside an otherwise empty object
    ],
)
def test_body_create_job_fold_preserves_surrounding_whitespace(request_data):
    """Whitespace is insignificant to a parser, but the fold claims to preserve every byte.

    Splicing the flag in must put the layout back: the indentation before the closing brace,
    the newline after it, and anything ahead of the opening brace. Otherwise the payload is
    quietly reformatted, which is the exact thing the splice exists to avoid.
    """
    folded = shared.BodyCreateJob(
        request_data=request_data, skip_preflight=True
    ).request_data

    # Removing exactly what was inserted must give back the original, byte for byte.
    inserted = '"skip_preflight": true'
    restored = folded.replace(f",{inserted}", "", 1) if f",{inserted}" in folded else folded.replace(inserted, "", 1)
    assert restored == request_data, (
        f"fold did not preserve the payload: {request_data!r} -> {folded!r}"
    )
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


def test_body_create_job_none_clears_a_previously_folded_flag():
    """Clearing the flag must clear it from the payload too.

    `None` is "no preference", which the server reads as not set. Leaving a stale
    `"skip_preflight": true` behind would run the job with preflight off *after* the caller
    cleared the flag - silent, and in the permissive direction.
    """
    body = shared.BodyCreateJob(request_data='{"a":1}', skip_preflight=True)
    assert json.loads(body.request_data)["skip_preflight"] is True

    body.skip_preflight = None
    assert "skip_preflight" not in json.loads(body.request_data)

    copied = shared.BodyCreateJob(
        request_data='{"a":1}', skip_preflight=True
    ).model_copy(update={"skip_preflight": None})
    assert "skip_preflight" not in json.loads(copied.request_data)


def test_body_create_job_unset_still_passes_a_caller_written_flag_through():
    """`Unset` and `None` are not the same, and only `None` may rewrite the payload.

    A caller who put `skip_preflight` in the JSON themselves and never touched the argument
    has said nothing for the SDK to override, so those bytes must survive verbatim. Clearing
    them here would be the SDK silently reversing the caller's own instruction.
    """
    written = '{"a":1,"skip_preflight":true}'
    assert shared.BodyCreateJob(request_data=written).request_data == written


@pytest.mark.parametrize(
    "request_data", ["not json at all", '{"x": 1e5}', "{}"]
)
def test_body_create_job_none_is_harmless_when_there_is_nothing_to_clear(request_data):
    """"No preference" has nothing to reject and nothing to rewrite.

    Unlike the True/False paths it must not raise on a non-JSON payload: nothing was folded
    into it, so there is nothing to undo.
    """
    assert (
        shared.BodyCreateJob(
            request_data=request_data, skip_preflight=None
        ).request_data
        == request_data
    )
