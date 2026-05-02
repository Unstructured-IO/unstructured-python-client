# CreateEmailChannelRequest

Request to create an email notification channel.


## Fields

| Field                                                                              | Type                                                                               | Required                                                                           | Description                                                                        |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `channel_type`                                                                     | *Optional[Literal["email"]]*                                                       | :heavy_minus_sign:                                                                 | N/A                                                                                |
| `description`                                                                      | *OptionalNullable[str]*                                                            | :heavy_minus_sign:                                                                 | Channel description                                                                |
| `email_config`                                                                     | [shared.EmailChannelConfig](../../models/shared/emailchannelconfig.md)             | :heavy_check_mark:                                                                 | User-configurable email settings.                                                  |
| `enabled`                                                                          | *Optional[bool]*                                                                   | :heavy_minus_sign:                                                                 | Enable/disable channel                                                             |
| `event_types`                                                                      | List[[shared.NotificationEventType](../../models/shared/notificationeventtype.md)] | :heavy_check_mark:                                                                 | Event types to subscribe to                                                        |