# document

### Available Operations

* [partition](#partition) - Pipeline 1

## partition

Pipeline 1

### Example Usage

```python
import unstructured
from unstructured.models import operations, shared

s = unstructured.Unstructured(
    security=shared.Security(
        api_key_auth="YOUR_API_KEY",
    ),
)

req = operations.PartitionRequest(
    document_submission=shared.DocumentSubmission(
        coordinates=[
            'magnam',
        ],
        encoding=[
            'debitis',
        ],
        files=[
            'ipsa'.encode(),
        ],
        gz_uncompressed_content_type='delectus',
        hi_res_model_name=[
            'tempora',
        ],
        include_page_breaks=[
            'suscipit',
        ],
        ocr_languages=[
            'molestiae',
        ],
        output_format='minus',
        pdf_infer_table_structure=[
            'placeat',
        ],
        skip_infer_table_types=[
            'voluptatum',
        ],
        strategy=[
            'iusto',
        ],
        xml_keep_tags=[
            'excepturi',
        ],
    ),
    unstructured_api_key='nisi',
)

res = s.document.partition(req)

if res.success is not None:
    # handle response
```

### Parameters

| Parameter                                                                  | Type                                                                       | Required                                                                   | Description                                                                |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `request`                                                                  | [operations.PartitionRequest](../../models/operations/partitionrequest.md) | :heavy_check_mark:                                                         | The request object to use for the request.                                 |


### Response

**[operations.PartitionResponse](../../models/operations/partitionresponse.md)**

