"""The verdict the Unstructured API declares beside ``detail`` in an error body.

Errors the API raises deliberately carry ``retryable``, ``error_type``,
``error_reason`` and ``audience`` next to ``detail``. Errors it did not classify
carry only ``detail``, and every field reads as ``None``.
"""

import json
from dataclasses import dataclass
from typing import Any, Optional, Union


@dataclass(frozen=True)
class DeclaredErrorFields:
    retryable: Optional[bool] = None
    error_type: Optional[str] = None
    error_reason: Optional[str] = None
    audience: Optional[str] = None


def _non_empty_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


def _declared_error_fields(body: Any) -> DeclaredErrorFields:
    if not isinstance(body, dict):
        return DeclaredErrorFields()
    retryable = body.get("retryable")
    return DeclaredErrorFields(
        retryable=retryable if isinstance(retryable, bool) else None,
        error_type=_non_empty_str(body.get("error_type")),
        error_reason=_non_empty_str(body.get("error_reason")),
        audience=_non_empty_str(body.get("audience")),
    )


def parse_declared_error_fields(raw: Union[str, bytes, None]) -> DeclaredErrorFields:
    """Read the declared fields from a raw body, dropping any of the wrong type.

    Bytes are decoded as JSON, which detects UTF-8, UTF-16 and UTF-32 and skips a
    UTF-8 byte order mark. A body that is not a JSON object declares nothing.
    """
    try:
        body = json.loads(raw) if raw else None
    except (ValueError, TypeError, RecursionError):
        return DeclaredErrorFields()
    return _declared_error_fields(body)
