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
Only the `files` parameter is required. See the [general partition](docs/sdks/general/README.md) page for all available parameters. 

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

filename = "sample-docs/layout-parser-paper.pdf"

with open(filename, "rb") as f:
    req = shared.PartitionParameters(
        files=shared.PartitionParametersFiles(
            content=f.read(),
            files=filename,
        )
    )
    
    res = s.general.partition(req)
    print(res.elements[0])

# {
#  'type': 'Title',
#  'element_id': '015301d4f56aa4b20ec10ac889d2343f',
#  'metadata': {'filename': 'layout-parser-paper.pdf', 'filetype': 'application/pdf', 'page_number': 1},
#  'text': 'LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis'
# }
```

## Change the base URL

If you are self hosting the API, or developing locally, you can change the server URL when setting up the client.

```python
s = UnstructuredClient()

# Using a local server
s.general.sdk_configuration.server_url = "http://localhost:8000"

# Using your own server
s.general.sdk_configuration.server_url = "https://your-server"
```

<!-- Start Dev Containers -->

<!-- End Dev Containers -->



## SDK Example Usage
<!-- Start SDK Example Usage -->


```python
import unstructured_client
from unstructured_client.models import shared

s = unstructured_client.UnstructuredClient(
    security=shared.Security(
        api_key_auth="YOUR_API_KEY",
    ),
)

req = shared.PartitionParameters(
    coordinates=False,
    encoding='utf-8',
    files=shared.PartitionParametersFiles(
        content='distinctio'.encode(),
        files='quibusdam',
    ),
    gz_uncompressed_content_type='application/pdf',
    hi_res_model_name='yolox',
    include_page_breaks=False,
    ocr_languages=[
        'eng',
    ],
    output_format='application/json',
    pdf_infer_table_structure=False,
    skip_infer_table_types=[
        'pdf',
    ],
    strategy='hi_res',
    xml_keep_tags=False,
)

res = s.general.partition(req)

if res.elements is not None:
    # handle response
```
<!-- End SDK Example Usage -->



<!-- Start SDK Available Operations -->
## Available Resources and Operations


### [general](docs/sdks/general/README.md)

* [partition](docs/sdks/general/README.md#partition) - Pipeline 1
<!-- End SDK Available Operations -->



<!-- Start Pagination -->
# Pagination

Some of the endpoints in this SDK support pagination. To use pagination, you make your SDK calls as usual, but the
returned response object will have a `Next` method that can be called to pull down the next group of results. If the
return value of `Next` is `None`, then there are no more pages to be fetched.

Here's an example of one such pagination call:


<!-- End Pagination -->

<!-- Placeholder for Future Speakeasy SDK Sections -->

### Maturity

This SDK is in beta, and there may be breaking changes between versions without a major version update. Therefore, we recommend pinning usage
to a specific package version. This way, you can install the same version each time without breaking changes unless you are intentionally
looking for the latest version.

### Contributions

While we value open-source contributions to this SDK, this library is generated programmatically.
Feel free to open a PR or a Github issue as a proof of concept and we'll do our best to include it in a future release!

### SDK Created by [Speakeasy](https://docs.speakeasyapi.dev/docs/using-speakeasy/client-sdks)
