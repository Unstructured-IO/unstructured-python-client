# NotificationEventType

Webhook event types derived from internal JOB_STATUSCHANGED_V1 statuses.

## Example Usage

```python
from unstructured_client.models.shared import NotificationEventType

value = NotificationEventType.JOB_SCHEDULED
```


## Values

| Name              | Value             |
| ----------------- | ----------------- |
| `JOB_SCHEDULED`   | job.scheduled     |
| `JOB_IN_PROGRESS` | job.in_progress   |
| `JOB_COMPLETED`   | job.completed     |
| `JOB_STOPPED`     | job.stopped       |
| `JOB_FAILED`      | job.failed        |