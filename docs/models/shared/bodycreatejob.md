# BodyCreateJob


## Fields

| Field                                                        | Type                                                         | Required                                                     | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `input_files`                                                | List[[shared.InputFiles](../../models/shared/inputfiles.md)] | :heavy_minus_sign:                                           | N/A                                                          |
| `request_data`                                               | *str*                                                        | :heavy_check_mark:                                           | JSON-encoded object. Provide either `template_id` or `job_nodes`, not both. Set `"skip_preflight": true` to skip the job preflight check for this job. |