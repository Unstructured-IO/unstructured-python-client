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

<!-- Start SDK Installation [installation] -->
## SDK Installation

```bash
pip install unstructured-client
```
<!-- End SDK Installation [installation] -->

## Usage
Only the `files` parameter is required. See the [general partition](docs/sdks/general/README.md) page for all available parameters. 

```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.models.errors import SDKError

s = UnstructuredClient(api_key_auth="YOUR_API_KEY")

filename = "_sample_docs/layout-parser-paper-fast.pdf"

with open(filename, "rb") as f:
    # Note that this currently only supports a single file
    files=shared.Files(
        content=f.read(),
        file_name=filename,
	)

req = shared.PartitionParameters(
    files=files,
    # Other partition params
    strategy='ocr_only',
    languages=["eng"],
)

try:
    resp = s.general.partition(req)
    print(resp.elements[0])
except SDKError as e:
    print(e)

# {
# 'type': 'UncategorizedText', 
# 'element_id': 'fc550084fda1e008e07a0356894f5816', 
# 'metadata': {
#   'filename': 'layout-parser-paper-fast.pdf', 
#   'filetype': 'application/pdf', 
#   'languages': ['eng'], 
#   'page_number': 1
#   }
# }
```

## Change the base URL

If you are self hosting the API, or developing locally, you can change the server URL when setting up the client.

```python
# Using a local server
s = unstructured_client.UnstructuredClient(
    server_url="http://localhost:8000",
    api_key_auth=api_key,
)

# Using your own server
s = unstructured_client.UnstructuredClient(
    server_url="https://your-server",
    api_key_auth=api_key,
)
```
<!-- No SDK Example Usage -->
<!-- No SDK Available Operations -->
<!-- No Pagination -->
<!-- No Error Handling -->
<!-- No Server Selection -->

<!-- Start Custom HTTP Client [http-client] -->
## Custom HTTP Client

The Python SDK makes API calls using the [requests](https://pypi.org/project/requests/) HTTP library.  In order to provide a convenient way to configure timeouts, cookies, proxies, custom headers, and other low-level configuration, you can initialize the SDK client with a custom `requests.Session` object.

For example, you could specify a header for every request that this sdk makes as follows:
```python
import unstructured_client
import requests

http_client = requests.Session()
http_client.headers.update({'x-custom-header': 'someValue'})
s = unstructured_client.UnstructuredClient(client: http_client)
```
<!-- End Custom HTTP Client [http-client] -->

<!-- No Retries -->
<!-- No Authentication -->

<!-- Placeholder for Future Speakeasy SDK Sections -->

### Maturity

This SDK is in beta, and there may be breaking changes between versions without a major version update. Therefore, we recommend pinning usage
to a specific package version. This way, you can install the same version each time without breaking changes unless you are intentionally
looking for the latest version.

### Contributions

While we value open-source contributions to this SDK, this library is generated programmatically.
Feel free to open a PR or a Github issue as a proof of concept and we'll do our best to include it in a future release!

### SDK Created by [Speakeasy](https://docs.speakeasyapi.dev/docs/using-speakeasy/client-sdks)

In order to start working with this repo, you need:
1. Install Speakeasy client locally https://github.com/speakeasy-api/speakeasy#installation
2. Run `speakeasy auth login`

Then put into local `openapi.json` the API for which you want to generate client,
and run `make sdk-generate`. This allows to iterate development with python client.

When preparing PR with changes, include in it only the human changes.
Once it's merged, Github CI will autogenerate the Speakeasy client in a new PR.
You will have to manually bring back the human created lines in it.
