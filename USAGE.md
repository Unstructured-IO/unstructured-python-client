<!-- Start SDK Example Usage [usage] -->
```python
import unstructured_client
from unstructured_client.models import shared

s = unstructured_client.UnstructuredClient(
    api_key_auth="YOUR_API_KEY",
)

req = shared.PartitionParameters(
    chunking_strategy='by_title',
    combine_under_n_chars=500,
    encoding='utf-8',
    files=shared.Files(
        content='0x2cC94b2FEF'.encode(),
        file_name='um.shtml',
    ),
    gz_uncompressed_content_type='application/pdf',
    hi_res_model_name='yolox',
    languages=[
        '[',
        'e',
        'n',
        'g',
        ']',
    ],
    max_characters=1500,
    new_after_n_chars=1500,
    output_format='application/json',
    skip_infer_table_types=[
        'pdf',
    ],
    strategy='hi_res',
)

res = s.general.partition(req)

if res.elements is not None:
    # handle response
    pass
```
<!-- End SDK Example Usage [usage] -->