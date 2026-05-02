# MarkReadRequest

Request to mark notifications as read.

Provide ONE of: notification_ids, before, or mark_all (mutually exclusive).
workflow_id is valid with 'before' or 'mark_all'.


## Fields

| Field                                                                 | Type                                                                  | Required                                                              | Description                                                           |
| --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `before`                                                              | [date](https://docs.python.org/3/library/datetime.html#date-objects)  | :heavy_minus_sign:                                                    | Mark all notifications created before this ISO 8601 timestamp as read |
| `mark_all`                                                            | *Optional[bool]*                                                      | :heavy_minus_sign:                                                    | Mark all unread notifications as read (can combine with workflow_id)  |
| `notification_ids`                                                    | List[*str*]                                                           | :heavy_minus_sign:                                                    | Specific notification IDs to mark as read (max 100)                   |
| `workflow_id`                                                         | *OptionalNullable[str]*                                               | :heavy_minus_sign:                                                    | Filter by workflow (only valid with 'before' or 'mark_all')           |