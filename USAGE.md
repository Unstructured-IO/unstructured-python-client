<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.create_connection_check_destinations(request={
        "destination_id": "d9795fb7-2135-4e48-a51d-009dd6ca38a1",
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

        res = await uc_client.destinations.create_connection_check_destinations_async(request={
            "destination_id": "d9795fb7-2135-4e48-a51d-009dd6ca38a1",
        })

        assert res.dag_node_connection_check is not None

        # Handle response
        print(res.dag_node_connection_check)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->