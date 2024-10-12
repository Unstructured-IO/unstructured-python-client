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
