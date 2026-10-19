"""The verdict the Unstructured API declares beside ``detail`` in an error body.

Errors the API raises deliberately carry ``retryable``, ``error_type``,
``error_reason`` and ``audience`` next to ``detail``. Errors it did not classify
carry only ``detail``, and every field reads as ``None``.
"""

import json
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class DeclaredErrorFields:
    retryable: Optional[bool] = None
    error_type: Optional[str] = None
    error_reason: Optional[str] = None
    audience: Optional[str] = None


def _non_empty_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


def declared_error_fields(body: Any) -> DeclaredErrorFields:
    """Read the declared fields from a decoded body, dropping any of the wrong type."""
    if not isinstance(body, dict):
        return DeclaredErrorFields()
    retryable = body.get("retryable")
    return DeclaredErrorFields(
        retryable=retryable if isinstance(retryable, bool) else None,
        error_type=_non_empty_str(body.get("error_type")),
        error_reason=_non_empty_str(body.get("error_reason")),
        audience=_non_empty_str(body.get("audience")),
    )


def parse_declared_error_fields(text: Optional[str]) -> DeclaredErrorFields:
    """Read the declared fields from a raw body; a non-JSON body declares nothing."""
    try:
        body = json.loads(text) if text else None
    except (ValueError, TypeError, RecursionError):
        return DeclaredErrorFields()
    return declared_error_fields(body)
