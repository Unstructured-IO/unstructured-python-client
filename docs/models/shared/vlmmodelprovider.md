# VLMModelProvider

The VLM Model provider to use.

## Example Usage

```python
from unstructured_client.models.shared import VLMModelProvider

value = VLMModelProvider.OPENAI

# Open enum: unrecognized values are captured as UnrecognizedStr
```


## Values

| Name                | Value               |
| ------------------- | ------------------- |
| `OPENAI`            | openai              |
| `ANTHROPIC`         | anthropic           |
| `BEDROCK`           | bedrock             |
| `ANTHROPIC_BEDROCK` | anthropic_bedrock   |
| `VERTEXAI`          | vertexai            |
| `GOOGLE`            | google              |
| `AZURE_OPENAI`      | azure_openai        |