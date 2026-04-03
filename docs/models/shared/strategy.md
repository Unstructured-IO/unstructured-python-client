# Strategy

The strategy to use for partitioning PDF/image. Options are fast, hi_res, auto. Default: hi_res

## Example Usage

```python
from unstructured_client.models.shared import Strategy

value = Strategy.FAST

# Open enum: unrecognized values are captured as UnrecognizedStr
```


## Values

| Name       | Value      |
| ---------- | ---------- |
| `FAST`     | fast       |
| `HI_RES`   | hi_res     |
| `AUTO`     | auto       |
| `OCR_ONLY` | ocr_only   |
| `OD_ONLY`  | od_only    |
| `VLM`      | vlm        |