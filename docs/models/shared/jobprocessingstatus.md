# JobProcessingStatus


## Values

| Name                    | Value                   |
| ----------------------- | ----------------------- |
| `SCHEDULED`             | SCHEDULED               |
| `IN_PROGRESS`           | IN_PROGRESS             |
| `SUCCESS`               | SUCCESS                 |
| `COMPLETED_WITH_ERRORS` | COMPLETED_WITH_ERRORS   |
| `STOPPED`               | STOPPED                 |
| `FAILED`                | FAILED                  |
| `REJECTED`              | REJECTED                |

An unrecognised value returned by the server is preserved verbatim as a pseudo-member
rather than raising, so a new server-side status is not a client break.
