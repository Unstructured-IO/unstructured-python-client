# KafkaCloudSourceConnectorConfigInput


## Fields

| Field                     | Type                      | Required                  | Description               |
| ------------------------- | ------------------------- | ------------------------- | ------------------------- |
| `bootstrap_servers`       | *str*                     | :heavy_check_mark:        | N/A                       |
| `kafka_api_key`           | *str*                     | :heavy_check_mark:        | N/A                       |
| `secret`                  | *str*                     | :heavy_check_mark:        | N/A                       |
| `topic`                   | *str*                     | :heavy_check_mark:        | N/A                       |
| `group_id`                | *OptionalNullable[str]*   | :heavy_minus_sign:        | N/A                       |
| `num_messages_to_consume` | *Optional[int]*           | :heavy_minus_sign:        | N/A                       |
| `port`                    | *Optional[int]*           | :heavy_minus_sign:        | N/A                       |