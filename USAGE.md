<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.create_destination(request={
        "create_destination_connector": {
            "config": {
                "api_endpoint": "<value>",
                "batch_size": 20,
                "collection_name": "<value>",
                "flatten_metadata": False,
                "token": "<value>",
            },
            "name": "<value>",
            "type": shared.DestinationConnectorType.AZURE,
        },
    })

    assert res.destination_connector_information is not None

    # Handle response
    print(res.destination_connector_information)
```

</br>

The same SDK client can also be used to make asychronous requests by importing asyncio.
```python
# Asynchronous Example
import asyncio
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared

async def main():

    async with UnstructuredClient() as uc_client:

        res = await uc_client.destinations.create_destination_async(request={
            "create_destination_connector": {
                "config": {
                    "api_endpoint": "<value>",
                    "batch_size": 20,
                    "collection_name": "<value>",
                    "flatten_metadata": False,
                    "token": "<value>",
                },
                "name": "<value>",
                "type": shared.DestinationConnectorType.AZURE,
            },
        })

        assert res.destination_connector_information is not None

        # Handle response
        print(res.destination_connector_information)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->