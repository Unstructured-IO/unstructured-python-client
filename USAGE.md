<!-- Start SDK Example Usage -->


```python
import unstructuredclient
from unstructuredclient.models import shared

s = unstructuredclient.UnstructuredClient(
    security=shared.Security(
        api_key_auth="YOUR_API_KEY",
    ),
)

req = shared.PartitionParameters(
    coordinates=False,
    encoding='utf-8',
    files=shared.PartitionParametersFiles(
        content='corrupti'.encode(),
        files='provident',
    ),
    gz_uncompressed_content_type='application/pdf',
    hi_res_model_name='yolox',
    include_page_breaks=False,
    ocr_languages=[
        'eng',
    ],
    output_format='application/json',
    pdf_infer_table_structure=False,
    skip_infer_table_types=[
        'pdf',
    ],
    strategy='hi_res',
    xml_keep_tags=False,
)

res = s.general.partition(req)

if res.partition_200_application_json_any is not None:
    # handle response
```
<!-- End SDK Example Usage -->