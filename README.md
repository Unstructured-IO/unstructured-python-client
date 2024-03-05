<h3 align="center">
  <img
    src="https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/img/unstructured_logo.png"
    height="200"
  >
</h3>

<div align="center">
    <a href="https://speakeasyapi.dev/"><img src="https://custom-icon-badges.demolab.com/badge/-Built%20By%20Speakeasy-212015?style=for-the-badge&logoColor=FBE331&logo=speakeasy&labelColor=545454" /></a>
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
Only the `files` parameter is required. 

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
```
    
Result:

```
{
'type': 'UncategorizedText', 
'element_id': 'fc550084fda1e008e07a0356894f5816', 
'metadata': {
  'filename': 'layout-parser-paper-fast.pdf', 
  'filetype': 'application/pdf', 
  'languages': ['eng'], 
  'page_number': 1
  }
}
```

### UnstructuredClient

#### Change the base URL

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

### PartitionParameters

See the [general partition](/docs/models/shared/partitionparameters.md) page for all available parameters. 

#### Splitting PDF by pages

In order to speed up processing of long PDF files, set `split_pdf_page=True`. It will cause the PDF
to be split page-by-page at client side, before sending to API, and combining individual responses
as single result. This will work only for PDF files, so don't set it for other filetypes.

Warning: this feature causes the `parent_id` metadata generation in elements to be disabled, as that
requires having context of multiple pages.

The amount of threads that will be used for sending individual pdf pages, is controlled by
`UNSTRUCTURED_CLIENT_SPLIT_CALL_THREADS` env var. By default it equals to 5. 
It can't be more than 15, to avoid too high resource usage and costs.

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

### Installation Instructions for Local Development

The following instructions are intended to help you get up and running with `unstructured-python-client` locally if you are planning to contribute to the project.

* Using `pyenv` to manage virtualenv's is recommended but not necessary
   * Mac install instructions. See [here](https://github.com/Unstructured-IO/community#mac--homebrew) for more detailed instructions.
      * `brew install pyenv-virtualenv`
      * `pyenv install 3.10`
   * Linux instructions are available [here](https://github.com/Unstructured-IO/community#linux).

* Create a virtualenv to work in and activate it, e.g. for one named `unstructured-python-client`:

  `pyenv  virtualenv 3.10 unstructured-python-client`
  `pyenv activate unstructured-python-client`

* Run `make install` and `make test`

### Contributions

While we value open-source contributions to this SDK, this library is generated programmatically by Speakeasy. In order to start working with this repo, you need to:
1. Install Speakeasy client locally https://github.com/speakeasy-api/speakeasy#installation
2. Run `speakeasy auth login`
3. Run `make client-generate`. This allows to iterate development with python client.

There are two important files used by `make client-generate`:
1. `openapi.json` which is actually not stored here, [but fetched from unstructured-api](https://raw.githubusercontent.com/Unstructured-IO/unstructured-api/main/openapi.json), represents the API that is supported on backend.
2. `overlay_client.yaml` is a handcrafted diff that when applied over above, produces `openapi_client.json` 
   which is used to generate SDK.

Once PR with changes is merged, Github CI will autogenerate the Speakeasy client in a new PR, using
the `openapi.json` and `overlay_client.yaml` You will have to manually bring back the human created lines in it.

Feel free to open a PR or a Github issue as a proof of concept and we'll do our best to include it in a future release!

### SDK Created by [Speakeasy](https://www.speakeasyapi.dev/docs/sdk-design/python/methodology-python)
