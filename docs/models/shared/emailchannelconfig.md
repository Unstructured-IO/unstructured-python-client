# EmailChannelConfig

User-configurable email settings.


## Fields

| Field                                     | Type                                      | Required                                  | Description                               |
| ----------------------------------------- | ----------------------------------------- | ----------------------------------------- | ----------------------------------------- |
| `cc`                                      | List[*str*]                               | :heavy_minus_sign:                        | CC email addresses (if provider supports) |
| `recipient_email`                         | *str*                                     | :heavy_check_mark:                        | Primary recipient email address           |
| `reply_to`                                | *OptionalNullable[str]*                   | :heavy_minus_sign:                        | Reply-to email address                    |