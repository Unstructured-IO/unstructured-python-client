<h3 align="center">
  <img
    src="https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/img/unstructured_logo.png"
    height="200"
  >
</h3>

<div align="center">
    <a href="https://speakeasyapi.dev/"><img src="https://custom-icon-badges.demolab.com/badge/-Built%20By%20Speakeasy-212015?style=for-the-badge&logoColor=FBE331&logo=speakeasy&labelColor=545454" /></a>
    <a href="https://github.com/Unstructured-IO/unstructured-client.git/actions"><img src="https://img.shields.io/github/actions/workflow/status/speakeasy-sdks/bolt-php/speakeasy_sdk_generation.yml?style=for-the-badge" /></a>
</div>

<h2 align="center">
  <p>Python SDK for the Unstructured API</p>
</h2>

This is a Python client for the [Unstructured API](https://unstructured-io.github.io/unstructured/api.html). 

<!-- Start SDK Installation -->
## SDK Installation

```bash
pip install unstructured-client
```
<!-- End SDK Installation -->

## Usage
Only the `files` parameter is required. See the [general partition]([General](docs/sdks/general/README.md)) page for all available parameters. 

```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared

# Note - in an upcoming release, the Security object is removed
# You'll pass the api key directly
s = UnstructuredClient(
    security=shared.Security(
        api_key_auth="YOUR_API_KEY",
    ),
)

filename = "/path/to/document"

with open(filename, "rb") as f:
    req = shared.PartitionParameters(
        files=shared.PartitionParametersFiles(
            content=f.read(),
            files=filename,
        )
    )
    
    res = s.general.partition(req)

    if res.partition_200_application_json_any is not None:
      # handle response
```

## Change the base URL

If you are self hosting the API, or developing locally, you can change the server URL when setting up the client.

```python
s = UnstructuredClient()

# Using a local server
s.config_server_url("http://localhost:8000")

# Using your own server
s.config_server_url("https://my-hosted-api")
```

<!-- Start Dev Containers -->

<!-- End Dev Containers -->

<!-- Placeholder for Future Speakeasy SDK Sections -->

### Maturity

This SDK is in beta, and there may be breaking changes between versions without a major version update. Therefore, we recommend pinning usage
to a specific package version. This way, you can install the same version each time without breaking changes unless you are intentionally
looking for the latest version.

### Contributions

While we value open-source contributions to this SDK, this library is generated programmatically.
Feel free to open a PR or a Github issue as a proof of concept and we'll do our best to include it in a future release!

### SDK Created by [Speakeasy](https://docs.speakeasyapi.dev/docs/using-speakeasy/client-sdks)
