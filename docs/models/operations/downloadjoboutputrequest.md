# DownloadJobOutputRequest


## Fields

| Field                                       | Type                                        | Required                                    | Description                                 |
| ------------------------------------------- | ------------------------------------------- | ------------------------------------------- | ------------------------------------------- |
| `file_id`                                   | *str*                                       | :heavy_check_mark:                          | ID of the file to download                  |
| `job_id`                                    | *str*                                       | :heavy_check_mark:                          | N/A                                         |
| `node_id`                                   | *OptionalNullable[str]*                     | :heavy_minus_sign:                          | Node ID to view per node output of the file |
| `unstructured_api_key`                      | *OptionalNullable[str]*                     | :heavy_minus_sign:                          | N/A                                         |