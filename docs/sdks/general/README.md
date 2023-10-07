# General
(*general*)

### Available Operations

* [partition](#partition) - Pipeline 1

## partition

Pipeline 1

### Example Usage

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
    encoding='utf-8',
    files=shared.PartitionParametersFiles(
        content='+WmI5Q)|yy'.encode(),
        files='um',
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
    new_after_n_chars=1500,
    output_format='application/json',
    skip_infer_table_types=[
        'p',
        'd',
        'f',
    ],
    strategy='hi_res',
)

res = s.general.partition(req)

if res.elements is not None:
    # handle response
```

### Parameters

| Parameter                                                                | Type                                                                     | Required                                                                 | Description                                                              |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `request`                                                                | [shared.PartitionParameters](../../models/shared/partitionparameters.md) | :heavy_check_mark:                                                       | The request object to use for the request.                               |
| `retries`                                                                | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)         | :heavy_minus_sign:                                                       | Configuration to override the default retry behavior of the client.      |


### Response

**[operations.PartitionResponse](../../models/operations/partitionresponse.md)**

