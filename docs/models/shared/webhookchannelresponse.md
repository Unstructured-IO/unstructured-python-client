# WebhookChannelResponse

Response for webhook notification channel.


## Fields

| Field                                                                | Type                                                                 | Required                                                             | Description                                                          |
| -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `channel_type`                                                       | *Optional[Literal["webhook"]]*                                       | :heavy_minus_sign:                                                   | N/A                                                                  |
| `created_at`                                                         | [date](https://docs.python.org/3/library/datetime.html#date-objects) | :heavy_check_mark:                                                   | Creation timestamp                                                   |
| `description`                                                        | *OptionalNullable[str]*                                              | :heavy_minus_sign:                                                   | Channel description                                                  |
| `enabled`                                                            | *bool*                                                               | :heavy_check_mark:                                                   | Channel enabled status                                               |
| `event_types`                                                        | List[*str*]                                                          | :heavy_check_mark:                                                   | Subscribed event types                                               |
| `id`                                                                 | *str*                                                                | :heavy_check_mark:                                                   | Channel ID                                                           |
| `updated_at`                                                         | [date](https://docs.python.org/3/library/datetime.html#date-objects) | :heavy_check_mark:                                                   | Last update timestamp                                                |
| `url`                                                                | *str*                                                                | :heavy_check_mark:                                                   | Webhook endpoint URL                                                 |