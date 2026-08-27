# BodyCreateJob


## Fields

| Field                                                        | Type                                                         | Required                                                     | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `input_files`                                                | List[[shared.InputFiles](../../models/shared/inputfiles.md)] | :heavy_minus_sign:                                           | N/A                                                          |
| `request_data`                                               | *str*                                                        | :heavy_check_mark:                                           | N/A                                                          |
| `skip_preflight`                                             | *OptionalNullable[bool]*                                     | :heavy_minus_sign:                                           | Skip the job preflight check for this job. Preflight runs by default. Folded into the `request_data` JSON on serialization rather than sent as its own form field. |