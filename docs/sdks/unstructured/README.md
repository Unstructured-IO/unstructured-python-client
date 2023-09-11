# Unstructured SDK

## Overview

### Available Operations

* [pipeline_1_general_v0_0_42_general_post](#pipeline_1_general_v0_0_42_general_post) - Pipeline 1
* [pipeline_1_general_v0_general_post](#pipeline_1_general_v0_general_post) - Pipeline 1

## pipeline_1_general_v0_0_42_general_post

Pipeline 1

### Example Usage

```python
import unstructured
from unstructured.models import operations, shared

s = unstructured.Unstructured()

req = operations.Pipeline1GeneralV0042GeneralPostRequest(
    body_pipeline_1_general_v0_0_42_general_post=shared.BodyPipeline1GeneralV0042GeneralPost(
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

res = s.unstructured.pipeline_1_general_v0_0_42_general_post(req)

if res.pipeline_1_general_v0_0_42_general_post_200_application_json_any is not None:
    # handle response
```

### Parameters

| Parameter                                                                                                                | Type                                                                                                                     | Required                                                                                                                 | Description                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                | [operations.Pipeline1GeneralV0042GeneralPostRequest](../../models/operations/pipeline1generalv0042generalpostrequest.md) | :heavy_check_mark:                                                                                                       | The request object to use for the request.                                                                               |


### Response

**[operations.Pipeline1GeneralV0042GeneralPostResponse](../../models/operations/pipeline1generalv0042generalpostresponse.md)**


## pipeline_1_general_v0_general_post

Pipeline 1

### Example Usage

```python
import unstructured
from unstructured.models import operations, shared

s = unstructured.Unstructured()

req = operations.Pipeline1GeneralV0GeneralPostRequest(
    body_pipeline_1_general_v0_general_post=shared.BodyPipeline1GeneralV0GeneralPost(
        coordinates=[
            'recusandae',
        ],
        encoding=[
            'temporibus',
        ],
        files=[
            'ab'.encode(),
        ],
        gz_uncompressed_content_type='quis',
        hi_res_model_name=[
            'veritatis',
        ],
        include_page_breaks=[
            'deserunt',
        ],
        ocr_languages=[
            'perferendis',
        ],
        output_format='ipsam',
        pdf_infer_table_structure=[
            'repellendus',
        ],
        skip_infer_table_types=[
            'sapiente',
        ],
        strategy=[
            'quo',
        ],
        xml_keep_tags=[
            'odit',
        ],
    ),
    unstructured_api_key='at',
)

res = s.unstructured.pipeline_1_general_v0_general_post(req)

if res.pipeline_1_general_v0_general_post_200_application_json_any is not None:
    # handle response
```

### Parameters

| Parameter                                                                                                          | Type                                                                                                               | Required                                                                                                           | Description                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                          | [operations.Pipeline1GeneralV0GeneralPostRequest](../../models/operations/pipeline1generalv0generalpostrequest.md) | :heavy_check_mark:                                                                                                 | The request object to use for the request.                                                                         |


### Response

**[operations.Pipeline1GeneralV0GeneralPostResponse](../../models/operations/pipeline1generalv0generalpostresponse.md)**

