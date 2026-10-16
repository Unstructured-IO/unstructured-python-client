"""Report API fields and enum values that the SDK's shared models do not cover.

Each component schema in the public OpenAPI specs is matched by name to a model or
enum in ``unstructured_client.models.shared``. A property missing from a model, or a
value missing from an enum, is drift. Drift recorded in the baseline file is
acknowledged; anything else, or a baseline entry that no longer applies, fails the
check.

    uv run python scripts/check_spec_drift.py
    uv run python scripts/check_spec_drift.py --update-baseline
"""

from __future__ import annotations

import argparse
import enum
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Set, Type, Union

import pydantic

from unstructured_client.models import shared

SPEC_URLS = [
    "https://platform.unstructuredapp.io/openapi.json",
    "https://api.unstructuredapp.io/general/openapi.json",
]
BASELINE_PATH = Path(__file__).with_name("spec_drift_baseline.json")

Drift = Dict[str, List[str]]
SdkType = Union[Type[pydantic.BaseModel], Type[enum.Enum]]


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _sdk_types() -> Dict[str, SdkType]:
    types: Dict[str, SdkType] = {}
    for name in dir(shared):
        obj = getattr(shared, name)
        if isinstance(obj, type) and issubclass(obj, (pydantic.BaseModel, enum.Enum)):
            types.setdefault(_normalize(name), obj)
    return types


def _fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def find_drift(specs: List[dict]) -> Drift:
    sdk_types = _sdk_types()
    drift: Dict[str, Set[str]] = {}
    for spec in specs:
        for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
            sdk_type = sdk_types.get(_normalize(schema_name))
            if sdk_type is None:
                continue
            if issubclass(sdk_type, enum.Enum):
                known = {str(member.value) for member in sdk_type}
                missing = {str(value) for value in schema.get("enum", [])} - known
            else:
                known = {f.alias or n for n, f in sdk_type.model_fields.items()}
                missing = set(schema.get("properties", {})) - known
            if missing:
                drift.setdefault(schema_name, set()).update(missing)
    return {name: sorted(values) for name, values in sorted(drift.items())}


def _subtract(drift: Drift, other: Drift) -> Drift:
    diff: Drift = {}
    for name, values in drift.items():
        extra = sorted(set(values) - set(other.get(name, [])))
        if extra:
            diff[name] = extra
    return diff


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Rewrite the baseline to acknowledge all current drift.",
    )
    args = parser.parse_args()

    current = find_drift([_fetch(url) for url in SPEC_URLS])

    if args.update_baseline:
        BASELINE_PATH.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {BASELINE_PATH}")
        return 0

    baseline: Drift = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    new = _subtract(current, baseline)
    stale = _subtract(baseline, current)

    for name, values in new.items():
        print(f"New drift: {name} is missing {', '.join(values)}")
    for name, values in stale.items():
        print(f"Stale baseline: {name} is no longer missing {', '.join(values)}")
    if new or stale:
        print(
            "\nUpdate the SDK models for new drift, or acknowledge it with "
            "--update-baseline. Remove stale entries with --update-baseline."
        )
        return 1

    print("No drift beyond the baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
