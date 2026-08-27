# JobStatus


## Values

| Name          | Value         |
| ------------- | ------------- |
| `SCHEDULED`   | SCHEDULED     |
| `IN_PROGRESS` | IN_PROGRESS   |
| `COMPLETED`   | COMPLETED     |
| `STOPPED`     | STOPPED       |
| `FAILED`      | FAILED        |
| `REJECTED`    | REJECTED      |

An unrecognised value returned by the server is preserved verbatim as a pseudo-member
rather than raising, so a new server-side status is not a client break.
