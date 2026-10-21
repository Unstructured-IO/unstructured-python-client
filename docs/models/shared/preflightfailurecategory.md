# PreflightFailureCategory

Stable, machine-routable category for a node that failed its preflight check.

## Values

| Name                        | Value                       |
| --------------------------- | --------------------------- |
| `AUTH_INVALID_CREDENTIAL`   | AUTH_INVALID_CREDENTIAL     |
| `AUTH_PERMISSION_DENIED`    | AUTH_PERMISSION_DENIED      |
| `AUTH_NETWORK_UNREACHABLE`  | AUTH_NETWORK_UNREACHABLE    |
| `AUTH_PROVIDER_UNAVAILABLE` | AUTH_PROVIDER_UNAVAILABLE   |
| `PROVIDER_RATE_LIMITED`     | PROVIDER_RATE_LIMITED       |
| `CONFIG_INVALID`            | CONFIG_INVALID              |
| `UNKNOWN`                   | UNKNOWN                     |

A category this version of the SDK does not recognize is returned as a plain `str` rather than raising; treat it as `UNKNOWN`.
