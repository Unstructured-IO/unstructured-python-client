# CreateWorkflow


## Fields

| Field                                                                | Type                                                                 | Required                                                             | Description                                                          |
| -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `destination_id`                                                     | *str*                                                                | :heavy_check_mark:                                                   | N/A                                                                  |
| `name`                                                               | *str*                                                                | :heavy_check_mark:                                                   | N/A                                                                  |
| `source_id`                                                          | *str*                                                                | :heavy_check_mark:                                                   | N/A                                                                  |
| `workflow_type`                                                      | [shared.WorkflowType](../../models/shared/workflowtype.md)           | :heavy_check_mark:                                                   | N/A                                                                  |
| `schedule`                                                           | [OptionalNullable[shared.Schedule]](../../models/shared/schedule.md) | :heavy_minus_sign:                                                   | N/A                                                                  |
| `workflow_nodes`                                                     | List[[shared.WorkflowNode](../../models/shared/workflownode.md)]     | :heavy_minus_sign:                                                   | N/A                                                                  |