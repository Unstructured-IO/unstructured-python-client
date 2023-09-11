<!-- Start SDK Example Usage -->


```python
import unstructured
from unstructured.models import operations, shared

s = unstructured.Unstructured()

req = operations.Pipeline1GeneralV0042GeneralPostRequest(
    body_pipeline_1_general_v0_0_42_general_post=shared.BodyPipeline1GeneralV0042GeneralPost(
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

res = s.pipeline_1_general_v0_0_42_general_post(req)

if res.pipeline_1_general_v0_0_42_general_post_200_application_json_any is not None:
    # handle response
```
<!-- End SDK Example Usage -->