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

A status value this version of the SDK does not recognize is returned as a plain `str` rather than raising.
