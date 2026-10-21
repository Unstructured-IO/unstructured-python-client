# JobDetails


## Fields

| Field                                                                    | Type                                                                     | Required                                                                 | Description                                                              |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `id`                                                                     | *str*                                                                    | :heavy_check_mark:                                                       | N/A                                                                      |
| `message`                                                                | *OptionalNullable[str]*                                                  | :heavy_minus_sign:                                                       | N/A                                                                      |
| `node_stats`                                                             | List[[shared.JobNodeDetails](../../models/shared/jobnodedetails.md)]     | :heavy_check_mark:                                                       | N/A                                                                      |
| `processing_status`                                                      | Union[[shared.JobProcessingStatus](../../models/shared/jobprocessingstatus.md), *str*] | :heavy_check_mark:                                                       | N/A                                                                      |