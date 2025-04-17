<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.check_destination_connection_api_v1_destinations_destination_id_connection_check_post(request={
        "destination_id": "b65169f5-79ba-4464-918f-b0be2c07b962",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)
```

</br>

The same SDK client can also be used to make asychronous requests by importing asyncio.
```python
# Asynchronous Example
import asyncio
from unstructured_client import UnstructuredClient

async def main():

    async with UnstructuredClient() as uc_client:

        res = await uc_client.destinations.check_destination_connection_api_v1_destinations_destination_id_connection_check_post_async(request={
            "destination_id": "b65169f5-79ba-4464-918f-b0be2c07b962",
        })

        assert res.dag_node_connection_check is not None

        # Handle response
        print(res.dag_node_connection_check)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->