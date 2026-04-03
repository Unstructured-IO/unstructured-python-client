# NotificationResponse

Single notification event.


## Fields

| Field                                                                | Type                                                                 | Required                                                             | Description                                                          |
| -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `created_at`                                                         | [date](https://docs.python.org/3/library/datetime.html#date-objects) | :heavy_check_mark:                                                   | Event creation timestamp                                             |
| `event_type`                                                         | *str*                                                                | :heavy_check_mark:                                                   | Event type (e.g., job.completed)                                     |
| `id`                                                                 | *str*                                                                | :heavy_check_mark:                                                   | Notification event UUID                                              |
| `is_read`                                                            | *Optional[bool]*                                                     | :heavy_minus_sign:                                                   | Read status for current user                                         |
| `payload`                                                            | Dict[str, *Any*]                                                     | :heavy_check_mark:                                                   | Event payload data                                                   |
| `workflow_id`                                                        | *OptionalNullable[str]*                                              | :heavy_minus_sign:                                                   | Workflow scope (null = account-level)                                |