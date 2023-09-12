# unstructured-client

<div align="left">
    <a href="https://speakeasyapi.dev/"><img src="https://custom-icon-badges.demolab.com/badge/-Built%20By%20Speakeasy-212015?style=for-the-badge&logoColor=FBE331&logo=speakeasy&labelColor=545454" /></a>
    <a href="https://github.com/Unstructured-IO/unstructured-client.git/actions"><img src="https://img.shields.io/github/actions/workflow/status/speakeasy-sdks/bolt-php/speakeasy_sdk_generation.yml?style=for-the-badge" /></a>
    
</div>

<!-- Start SDK Installation -->
## SDK Installation

```bash
pip install git+https://github.com/Unstructured-IO/unstructured-python-client.git
```
<!-- End SDK Installation -->

## SDK Example Usage
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

<!-- Start SDK Available Operations -->
## Available Resources and Operations

### [Unstructured SDK](docs/sdks/unstructured/README.md)

* [pipeline_1_general_v0_0_42_general_post](docs/sdks/unstructured/README.md#pipeline_1_general_v0_0_42_general_post) - Pipeline 1
* [pipeline_1_general_v0_general_post](docs/sdks/unstructured/README.md#pipeline_1_general_v0_general_post) - Pipeline 1
<!-- End SDK Available Operations -->

### Maturity

This SDK is in beta, and there may be breaking changes between versions without a major version update. Therefore, we recommend pinning usage
to a specific package version. This way, you can install the same version each time without breaking changes unless you are intentionally
looking for the latest version.

### Contributions

While we value open-source contributions to this SDK, this library is generated programmatically.
Feel free to open a PR or a Github issue as a proof of concept and we'll do our best to include it in a future release!

### SDK Created by [Speakeasy](https://docs.speakeasyapi.dev/docs/using-speakeasy/client-sdks)
