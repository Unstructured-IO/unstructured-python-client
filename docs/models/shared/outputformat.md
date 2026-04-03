# OutputFormat

The format of the response. Supported formats are application/json and text/csv. Default: application/json.

## Example Usage

```python
from unstructured_client.models.shared import OutputFormat

value = OutputFormat.APPLICATION_JSON

# Open enum: unrecognized values are captured as UnrecognizedStr
```


## Values

| Name               | Value              |
| ------------------ | ------------------ |
| `APPLICATION_JSON` | application/json   |
| `TEXT_CSV`         | text/csv           |