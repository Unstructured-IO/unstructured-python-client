<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.create_connection_check_destinations(security=operations.CreateConnectionCheckDestinationsSecurity(
        http_bearer="<YOUR_BEARER_TOKEN_HERE>",
    ), request={
        "destination_id": "cb9e35c1-0b04-4d98-83fa-fa6241323f96",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.
```python
# Asynchronous Example
import asyncio
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations

async def main():

    async with UnstructuredClient() as uc_client:

        res = await uc_client.destinations.create_connection_check_destinations_async(security=operations.CreateConnectionCheckDestinationsSecurity(
            http_bearer="<YOUR_BEARER_TOKEN_HERE>",
        ), request={
            "destination_id": "cb9e35c1-0b04-4d98-83fa-fa6241323f96",
        })

        assert res.dag_node_connection_check is not None

        # Handle response
        print(res.dag_node_connection_check)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->