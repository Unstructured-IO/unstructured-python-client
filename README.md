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

<div align="center">

 <a
   href="https://www.phorm.ai/query?projectId=34efc517-2201-4376-af43-40c4b9da3dc5">
	<img src="https://img.shields.io/badge/Phorm-Ask_AI-%23F2777A.svg?&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNSIgaGVpZ2h0PSI0IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogIDxwYXRoIGQ9Ik00LjQzIDEuODgyYTEuNDQgMS40NCAwIDAgMS0uMDk4LjQyNmMtLjA1LjEyMy0uMTE1LjIzLS4xOTIuMzIyLS4wNzUuMDktLjE2LjE2NS0uMjU1LjIyNmExLjM1MyAxLjM1MyAwIDAgMS0uNTk1LjIxMmMtLjA5OS4wMTItLjE5Mi4wMTQtLjI3OS4wMDZsLTEuNTkzLS4xNHYtLjQwNmgxLjY1OGMuMDkuMDAxLjE3LS4xNjkuMjQ2LS4xOTFhLjYwMy42MDMgMCAwIDAgLjItLjEwNi41MjkuNTI5IDAgMCAwIC4xMzgtLjE3LjY1NC42NTQgMCAwIDAgLjA2NS0uMjRsLjAyOC0uMzJhLjkzLjkzIDAgMCAwLS4wMzYtLjI0OS41NjcuNTY3IDAgMCAwLS4xMDMtLjIuNTAyLjUwMiAwIDAgMC0uMTY4LS4xMzguNjA4LjYwOCAwIDAgMC0uMjQtLjA2N0wyLjQzNy43MjkgMS42MjUuNjcxYS4zMjIuMzIyIDAgMCAwLS4yMzIuMDU4LjM3NS4zNzUgMCAwIDAtLjExNi4yMzJsLS4xMTYgMS40NS0uMDU4LjY5Ny0uMDU4Ljc1NEwuNzA1IDRsLS4zNTctLjA3OUwuNjAyLjkwNkMuNjE3LjcyNi42NjMuNTc0LjczOS40NTRhLjk1OC45NTggMCAwIDEgLjI3NC0uMjg1Ljk3MS45NzEgMCAwIDEgLjMzNy0uMTRjLjExOS0uMDI2LjIyNy0uMDM0LjMyNS0uMDI2TDMuMjMyLjE2Yy4xNTkuMDE0LjMzNi4wMy40NTkuMDgyYTEuMTczIDEuMTczIDAgMCAxIC41NDUuNDQ3Yy4wNi4wOTQuMTA5LjE5Mi4xNDQuMjkzYTEuMzkyIDEuMzkyIDAgMCAxIC4wNzguNThsLS4wMjkuMzJaIiBmaWxsPSIjRjI3NzdBIi8+CiAgPHBhdGggZD0iTTQuMDgyIDIuMDA3YTEuNDU1IDEuNDU1IDAgMCAxLS4wOTguNDI3Yy0uMDUuMTI0LS4xMTQuMjMyLS4xOTIuMzI0YTEuMTMgMS4xMyAwIDAgMS0uMjU0LjIyNyAxLjM1MyAxLjM1MyAwIDAgMS0uNTk1LjIxNGMtLjEuMDEyLS4xOTMuMDE0LS4yOC4wMDZsLTEuNTYtLjEwOC4wMzQtLjQwNi4wMy0uMzQ4IDEuNTU5LjE1NGMuMDkgMCAuMTczLS4wMS4yNDgtLjAzM2EuNjAzLjYwMyAwIDAgMCAuMi0uMTA2LjUzMi41MzIgMCAwIDAgLjEzOS0uMTcyLjY2LjY2IDAgMCAwIC4wNjQtLjI0MWwuMDI5LS4zMjFhLjk0Ljk0IDAgMCAwLS4wMzYtLjI1LjU3LjU3IDAgMCAwLS4xMDMtLjIwMi41MDIuNTAyIDAgMCAwLS4xNjgtLjEzOC42MDUuNjA1IDAgMCAwLS4yNC0uMDY3TDEuMjczLjgyN2MtLjA5NC0uMDA4LS4xNjguMDEtLjIyMS4wNTUtLjA1My4wNDUtLjA4NC4xMTQtLjA5Mi4yMDZMLjcwNSA0IDAgMy45MzhsLjI1NS0yLjkxMUExLjAxIDEuMDEgMCAwIDEgLjM5My41NzIuOTYyLjk2MiAwIDAgMSAuNjY2LjI4NmEuOTcuOTcgMCAwIDEgLjMzOC0uMTRDMS4xMjIuMTIgMS4yMy4xMSAxLjMyOC4xMTlsMS41OTMuMTRjLjE2LjAxNC4zLjA0Ny40MjMuMWExLjE3IDEuMTcgMCAwIDEgLjU0NS40NDhjLjA2MS4wOTUuMTA5LjE5My4xNDQuMjk1YTEuNDA2IDEuNDA2IDAgMCAxIC4wNzcuNTgzbC0uMDI4LjMyMloiIGZpbGw9IndoaXRlIi8+CiAgPHBhdGggZD0iTTQuMDgyIDIuMDA3YTEuNDU1IDEuNDU1IDAgMCAxLS4wOTguNDI3Yy0uMDUuMTI0LS4xMTQuMjMyLS4xOTIuMzI0YTEuMTMgMS4xMyAwIDAgMS0uMjU0LjIyNyAxLjM1MyAxLjM1MyAwIDAgMS0uNTk1LjIxNGMtLjEuMDEyLS4xOTMuMDE0LS4yOC4wMDZsLTEuNTYtLjEwOC4wMzQtLjQwNi4wMy0uMzQ4IDEuNTU5LjE1NGMuMDkgMCAuMTczLS4wMS4yNDgtLjAzM2EuNjAzLjYwMyAwIDAgMCAuMi0uMTA2LjUzMi41MzIgMCAwIDAgLjEzOS0uMTcyLjY2LjY2IDAgMCAwIC4wNjQtLjI0MWwuMDI5LS4zMjFhLjk0Ljk0IDAgMCAwLS4wMzYtLjI1LjU3LjU3IDAgMCAwLS4xMDMtLjIwMi41MDIuNTAyIDAgMCAwLS4xNjgtLjEzOC42MDUuNjA1IDAgMCAwLS4yNC0uMDY3TDEuMjczLjgyN2MtLjA5NC0uMDA4LS4xNjguMDEtLjIyMS4wNTUtLjA1My4wNDUtLjA4NC4xMTQtLjA5Mi4yMDZMLjcwNSA0IDAgMy45MzhsLjI1NS0yLjkxMUExLjAxIDEuMDEgMCAwIDEgLjM5My41NzIuOTYyLjk2MiAwIDAgMSAuNjY2LjI4NmEuOTcuOTcgMCAwIDEgLjMzOC0uMTRDMS4xMjIuMTIgMS4yMy4xMSAxLjMyOC4xMTlsMS41OTMuMTRjLjE2LjAxNC4zLjA0Ny40MjMuMWExLjE3IDEuMTcgMCAwIDEgLjU0NS40NDhjLjA2MS4wOTUuMTA5LjE5My4xNDQuMjk1YTEuNDA2IDEuNDA2IDAgMCAxIC4wNzcuNTgzbC0uMDI4LjMyMloiIGZpbGw9IndoaXRlIi8+Cjwvc3ZnPgo=" />
   </a>

</div>

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

In order to speed up processing of long PDF files, `split_pdf_page` is set to `True` by default. It will cause the PDF
to be split at client side, before sending to API, and combining individual responses
as single result. This parameter will affect only PDF files, no need to disable it for other filetypes.
The splitting behavior can be disabled by setting `split_pdf_page=False`.

Warning: this feature causes the `parent_id` metadata generation in elements to be disabled, as that
requires having context of multiple pages.

The amount of workers utilized for splitting PDFs is dictated by the `split_pdf_concurrency_level` parameter, with a default of 5 and a maximum of 15 to keep resource usage and costs in check.
The size of each batch of pages (ranging from 2 to 20), is internally determined based on the concurrency level and the total number of pages in the document.

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
s = unstructured_client.UnstructuredClient(client=http_client)
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
