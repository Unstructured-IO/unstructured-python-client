# EmailChannelConfigResponse

Email config in response (no sensitive data).


## Fields

| Field                                            | Type                                             | Required                                         | Description                                      |
| ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ |
| `cc`                                             | List[*str*]                                      | :heavy_minus_sign:                               | CC email addresses (if provider supports)        |
| `provider`                                       | *str*                                            | :heavy_check_mark:                               | Email provider (read-only, from platform config) |
| `recipient_email`                                | *str*                                            | :heavy_check_mark:                               | Primary recipient email address                  |
| `reply_to`                                       | *OptionalNullable[str]*                          | :heavy_minus_sign:                               | Reply-to email address                           |