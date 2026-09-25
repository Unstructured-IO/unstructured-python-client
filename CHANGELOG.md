## 0.46.2

### Fixes
* Accept the API URL the Transform Platform hands you as `server_url`. The app's API Keys page and the docs give you `https://platform-api.transform.unstructured.io/api/v1`, which works with curl but 404'd every Platform call in the SDK: the URL cleaner only stripped a path for `unstructuredapp.io` hosts, so the `/api/v1` survived and the operation's own `/api/v1/jobs/` was appended on top, producing `/api/v1/api/v1/jobs/`. Hosts under `unstructured.io` are now recognized too, and are matched on domain boundaries so a lookalike host like `unstructuredapp.io.example.com` keeps its path and scheme. A `server_url` passed to an individual operation is cleaned as well — previously only the client-level URL was, so `client.jobs.list_jobs(request={}, server_url=...)` still 404'd.

## 0.46.1

### Fixes
* Fail loudly when a split-PDF chunk returns HTTP 200 with an empty JSON body in NDJSON elements-file mode. The chunk used to be logged and skipped, so the combined `elements_file` was silently short by those pages while the call still returned 200 — and `split_pdf_allow_failed=False` did not catch it, because an empty 200 counts as a successful chunk. Recombination now raises `EmptyChunkResponseError` (a `ValueError`), matching the buffered path, which raises `JSONDecodeError` on the same response. Emptiness is judged against the chunk's own `Content-Type`: JSON has no empty document (a chunk with no elements is `[]`), while `application/x-ndjson` encodes zero records as zero lines, so an empty NDJSON chunk is well formed and still contributes nothing.

## 0.46.0

### Features
* Add an NDJSON elements-file mode to `partition()`. Pass `accept_header_override=PartitionAcceptEnum.APPLICATION_X_NDJSON` to get `PartitionResponse.elements_file` — a path to an NDJSON file with one element per line — instead of `PartitionResponse.elements`. On the split-PDF path the per-chunk temp files are concatenated on disk rather than parsed, flattened, re-serialized with `json.dumps` and re-parsed by the SDK, which held four copies of the document in memory at once; peak memory becomes roughly one chunk instead of the whole document. `elements_file` is set for every input, including ones that are not split and responses from a server that ignores the `Accept` header, so callers need only one code path — but the memory saving itself applies only to split PDFs (a PDF of more than two pages, with `split_pdf_page=True`). **The caller owns the returned file and is responsible for deleting it.** Requesting `application/json` (the default) is unchanged.

## 0.45.0

### Features
* Make the split-PDF `httpx.AsyncClient` connection-pool limits configurable via env vars: `UNSTRUCTURED_CLIENT_MAX_CONNECTIONS` (default `100`), `UNSTRUCTURED_CLIENT_MAX_KEEPALIVE_CONNECTIONS` (default `20`), and `UNSTRUCTURED_CLIENT_KEEPALIVE_EXPIRY` (default `5.0`s). Defaults match httpx, so behavior is unchanged unless set. Useful when deploying behind a connect-time-only load balancer (e.g. Kubernetes ClusterIP without a mesh) where shorter keepalives force connections to redistribute across backend pods.
* Honor the standard `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` env vars to point the split-PDF `httpx.AsyncClient` at a custom trust store, so a single env-var setting applies uniformly across Python tooling.
* Add `UNSTRUCTURED_CLIENT_TLS_CLIENT_CERT` and `UNSTRUCTURED_CLIENT_TLS_CLIENT_KEY` env vars to wire an mTLS client certificate into the split-PDF `httpx.AsyncClient` (single PEM, or split cert + key files).
* Extend the split-PDF `event=plan_created` log to include the resolved pool limits and trust-store / mTLS mode so the active config is visible in production logs.

## 0.44.1

### Features
* Add `min_attempts` and `absolute_max_elapsed_time_ms` fields to `BackoffStrategy`. `min_attempts` is the minimum number of retry attempts that must fire before `max_elapsed_time` is honored; defaults to `0` (preserves existing behavior). `absolute_max_elapsed_time_ms` caps when a new retry can start (does not interrupt in-flight requests); defaults to `None`. Together these close a short-circuit where a single slow first attempt could exhaust the retry budget before any retry fired.

## 0.44.0

### Breaking changes
* Removed deprecated connector config models from the SDK (e.g. `S3SourceConnectorConfig`, `AzureDestinationConnectorConfig`). Pass connector configs as plain dicts with arbitrary fields. The SDK is no longer coupled to backend connector schemas — new fields work without an SDK upgrade.

## 0.43.4

### Enhancements

### Features

### Fixes
* Route split-PDF `partition_async()` result collection through awaited async hook dispatch instead of creating a nested event loop in a worker thread.
  Sync-only hooks on the async path now run on a worker thread, so hook code that depends on event-loop-thread `contextvars` or thread-local state should pass that state explicitly.
* Add cancellation cleanup for in-flight split-PDF chunk tasks and preserve existing sync `partition()` split-PDF behavior with lazy executor creation.

## 0.43.2

### Enhancements
* Switch PyPI publishing to GitHub trusted publishing so releases can publish via OIDC without a long-lived `PYPI_TOKEN` secret.

### Features

### Fixes
* Align release automation, package metadata, and generator config on `0.43.2` for the trusted-publishing release flow.

## 0.43.1

### Enhancements
* Add split-PDF observability with operation-aware batch planning, timeout, cancellation, and completion logs.
* Make long-running integration tests stream live progress, timings, and backend failure context for split and single partition phases.

### Features

### Fixes
* Preserve chunk-local transport retries for split-PDF execution even when SDK-level retries disable connection-error retries for top-level requests.
* Harden split-PDF timeout and cleanup paths against closed event loops and cancelled chunk tasks.
* Stabilize `hi_res` split integration coverage by using a smaller derived multi-page fixture instead of the flaky full `layout-parser-paper.pdf` path for equivalence and caching checks.

## 0.42.12

### Enhancements

### Features

### Fixes
* Retry on all `httpx.TransportError` subclasses (including `ReadError`, `WriteError`, `ConnectError`, `RemoteProtocolError`, and all timeout types) when `retry_connection_errors=True`. Previously only `ConnectError`, `RemoteProtocolError`, and `TimeoutException` were retried — `ReadError` (TCP connection reset mid-response) was treated as permanent.

## 0.42.11

### Enhancements

### Features

### Fixes
* Retry on `httpx.RemoteProtocolError` (e.g. "Server disconnected without sending a response") when `retry_connection_errors=True`. Previously, mid-request server crashes were treated as permanent errors and not retried.

## 0.42.5

### Enhancements
* Support for on-demand jobs via CreateJob API
* New Read-only APIs GetTemplate and ListTemplates

### Features

### Fixes

## 0.42.4

### Enhancements
* Bump dependencies to account for vulnerabilities in pypdf < 6.1.3

### Features

### Fixes

## 0.42.3

### Enhancements

### Features
* Enable arbitrary dictionary inputs for `CreateSourceConnectorConfig` and `CreateDestinationConnectorConfig`. This decouples us from the backend schemas. Users can send new connector config fields without having to upgrade their client.

### Fixes

## 0.42.2

### Enhancements

### Features
* Enable arbitrary inputs for `SourceConnectorType` and `DestinationConnectorType`. This lets the client support new connector types without having to upgrade.

### Fixes

## 0.42.1

### Enhancements

### Features

### Fixes
* potential issue referencing models before declaration (commit by @mfbx9da4)

## 0.42.0

### Enhancements

### Features

### Fixes
* Fix some environments failing to split pdfs with `Can't patch loop of type <class 'uvloop.Loop'>`, remove usage of `nest-asyncio`
* Remove some operations under `client.users` that are not fully ready yet

## 0.41.0

### Enhancements

### Features
* Provide a base `UnstructuredClientError` to capture every error raised by the SDK. Note that some exceptions such as `SDKError` now have more information in the `message` field. This will impact any users who rely on string matching in their error handling.

### Fixes

## 0.37.3

### Enhancements
* Improve PDF validation error handling by introducing FileValidationError base class for better error abstraction

### Features

### Fixes
* Replace RequestError with PDFValidationError for invalid PDF files to provide more accurate error context

## 0.37.0

### Enhancements

### Features

### Fixes
* Throws appropriate error message in case the given PDF file is invalid (corrupted or encrypted).

## 0.30.0

### Enhancements

### Features
* Add Unstructured Platform APIs to manage source and destination connectors, workflows, and workflow runs
__WARNING__: This is a breaking change for the use of non-default `server_url` settings in the client usage.
To set the custom URL for the client, use the the `server_url` parameter in a given operation:
```python
elements = client.general.partition(
    request=operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=shared.Files(
                content=doc_file,
                file_name="your_document.pdf",
            ),
            strategy=shared.Strategy.FAST,
        )
    ),
    server_url="your_server_url",
)
```

### Fixes

## 0.26.1

### Enhancements

### Features

### Fixes
* Use the configured server_url for our split page "dummy" request

## 0.26.0

### Enhancements
* Switch to a httpx based client instead of requests
* Switch to poetry for dependency management
* Add client side parameter checking via Pydantic or TypedDict interfaces

### Features
* Add `partition_async` for a non blocking alternative to `partition`

### Fixes
* Address some asyncio based errors in pdf splitting logic
