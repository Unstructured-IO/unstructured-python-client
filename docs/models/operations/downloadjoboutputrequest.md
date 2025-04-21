# DownloadJobOutputRequest


## Fields

| Field                                             | Type                                              | Required                                          | Description                                       |
| ------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------- |
| `file_id`                                         | *str*                                             | :heavy_check_mark:                                | ID of the file to download                        |
| `job_id`                                          | *str*                                             | :heavy_check_mark:                                | N/A                                               |
| `node_id`                                         | *str*                                             | :heavy_check_mark:                                | Node ID to retrieve the corresponding output file |
| `unstructured_api_key`                            | *OptionalNullable[str]*                           | :heavy_minus_sign:                                | N/A                                               |