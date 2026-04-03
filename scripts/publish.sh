#!/usr/bin/env bash
set -euo pipefail

# Verify Python >= 3.11 is available (the Speakeasy publish action may only
# provide 3.10; uv auto-downloads a compatible interpreter by default, but
# this guard ensures a clear error if that mechanism is disabled).
uv run python -c "
import sys
if sys.version_info < (3, 11):
    sys.exit(f'Python >= 3.11 required, got {sys.version}')
"

uv run python scripts/prepare_readme.py

uv build --out-dir dist --clear
uv publish --token "${PYPI_TOKEN}" --check-url https://pypi.org/simple
