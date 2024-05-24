<!-- Start SDK Example Usage [usage] -->
```python
import unstructured_client
from unstructured_client.models import operations, shared

s = unstructured_client.UnstructuredClient(
    api_key_auth="YOUR_API_KEY",
)


res = s.general.partition(request=operations.PartitionRequest(
    partition_parameters=shared.PartitionParameters(
        files=shared.Files(
            content='0x2cC94b2FEF'.encode(),
            file_name='um.shtml',
        ),
        strategy=shared.Strategy.HI_RES,
    ),
))

if res.elements is not None:
    # handle response
    pass

```
<!-- End SDK Example Usage [usage] -->