<!-- Start SDK Example Usage -->


```python
import unstructured_client
from unstructured_client.models import shared

s = unstructured_client.UnstructuredClient(
    security=shared.Security(
        api_key_auth="YOUR_API_KEY",
    ),
)

req = shared.PartitionParameters(
    chunking_strategy='by_title',
    combine_under_n_chars=500,
    coordinates=False,
    encoding='utf-8',
    files=shared.PartitionParametersFiles(
        content='+WmI5Q)|yy'.encode(),
        files='um',
    ),
    gz_uncompressed_content_type='application/pdf',
    hi_res_model_name='yolox',
    include_page_breaks=False,
    languages=[
        'eng',
    ],
    multipage_sections=False,
    new_after_n_chars=1500,
    output_format='application/json',
    pdf_infer_table_structure=False,
    skip_infer_table_types=[
        'pdf',
    ],
    strategy='hi_res',
    xml_keep_tags=False,
)

res = s.general.partition(req)

if res.elements is not None:
    # handle response
```
<!-- End SDK Example Usage -->