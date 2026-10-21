# Contributing to This Repository

Thank you for your interest in contributing to this repository. We do not currently accept direct changes or pull requests. Instead, we encourage you to follow the guidelines below to report issues and suggest improvements.

## How to Report Issues

If you encounter any bugs or have suggestions for improvements, please open an issue on GitHub. When reporting an issue, please provide as much detail as possible to help us reproduce the problem. This includes:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected and actual behavior
- Any relevant logs, screenshots, or error messages
- Information about your environment (e.g., operating system, software versions)
    - For example can be collected using the `npx envinfo` command from your terminal if you have Node.js installed

## Issue Triage and Upstream Fixes

We will review and triage issues as quickly as possible. Our goal is to address bugs and incorporate improvements in the next release.

## Keeping models in sync with the API

The models under `src/unstructured_client/models/` are maintained by hand. They are no longer regenerated from the API's OpenAPI spec, so a field or enum value added on the server does not reach this SDK until someone adds it.

`make check-spec-drift` compares the public specs (`https://platform.unstructuredapp.io/openapi.json` and `https://api.unstructuredapp.io/general/openapi.json`) with the models in `unstructured_client.models.shared`. It reports every property and enum value the spec has that the matching model lacks. Gaps the SDK does not cover yet are recorded in `scripts/spec_drift_baseline.json`, so the check fails only on new drift, or on a baseline entry that no longer applies.

The `API spec drift` workflow runs the check every Monday and opens or comments on an issue when it fails. To resolve it:

1. Add new fields and enum values to the models, and update the matching page under `docs/models/`.
   * A new enum value on a response model is the case that breaks callers. A closed enum raises on a value it does not know, and one bad item fails a whole list response. Response fields whose enum is expected to grow should accept unknown values. See `JobInformation.status` for the pattern: `Union[<Enum>, UnrecognizedStr]` with `union_mode="left_to_right"`.
2. Acknowledge any gap you are deliberately not covering, and clear entries the SDK now covers, with `uv run python scripts/check_spec_drift.py --update-baseline`.
3. Add a `CHANGELOG.md` entry and bump `src/unstructured_client/_version.py`.

## Contact

If you have any questions or need further assistance, please feel free to reach out by opening an issue.

Thank you for your understanding and cooperation!

The Maintainers
