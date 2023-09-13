<!-- Start SDK Example Usage -->


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
            'corrupti',
        ],
        encoding=[
            'provident',
        ],
        files=[
            'distinctio'.encode(),
        ],
        gz_uncompressed_content_type='quibusdam',
        hi_res_model_name=[
            'unde',
        ],
        include_page_breaks=[
            'nulla',
        ],
        ocr_languages=[
            'corrupti',
        ],
        output_format='illum',
        pdf_infer_table_structure=[
            'vel',
        ],
        skip_infer_table_types=[
            'error',
        ],
        strategy=[
            'deserunt',
        ],
        xml_keep_tags=[
            'suscipit',
        ],
    ),
    unstructured_api_key='iure',
)

res = s.document.partition(req)

if res.success is not None:
    # handle response
```
<!-- End SDK Example Usage -->