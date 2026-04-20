# NotificationListResponse

Paginated notification list response.


## Fields

| Field                                                                            | Type                                                                             | Required                                                                         | Description                                                                      |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `events`                                                                         | List[[shared.NotificationResponse](../../models/shared/notificationresponse.md)] | :heavy_check_mark:                                                               | List of notification events                                                      |
| `next_cursor`                                                                    | *OptionalNullable[str]*                                                          | :heavy_minus_sign:                                                               | Cursor for next page (null if no more)                                           |