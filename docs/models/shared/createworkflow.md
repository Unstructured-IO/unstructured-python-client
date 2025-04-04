# CreateWorkflow


## Fields

| Field                                                                | Type                                                                 | Required                                                             | Description                                                          |
| -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `name`                                                               | *str*                                                                | :heavy_check_mark:                                                   | N/A                                                                  |
| `workflow_type`                                                      | [shared.WorkflowType](../../models/shared/workflowtype.md)           | :heavy_check_mark:                                                   | N/A                                                                  |
| `destination_id`                                                     | *OptionalNullable[str]*                                              | :heavy_minus_sign:                                                   | N/A                                                                  |
| `schedule`                                                           | [OptionalNullable[shared.Schedule]](../../models/shared/schedule.md) | :heavy_minus_sign:                                                   | N/A                                                                  |
| `source_id`                                                          | *OptionalNullable[str]*                                              | :heavy_minus_sign:                                                   | N/A                                                                  |
| `workflow_nodes`                                                     | List[[shared.WorkflowNode](../../models/shared/workflownode.md)]     | :heavy_minus_sign:                                                   | N/A                                                                  |