# Localhost development

The file `openapi.json` is copied here from https://raw.githubusercontent.com/Unstructured-IO/unstructured-api/main/openapi.json
and represents the API that is supported on backend.

The `openapi_client.json` is stored here, and treated as a source of truth for what should be accepted in python client.
The idea is, that it is easier to maintain this file showing exactly what we support, instead of handcrafting overlays.

When `openapi.json` and `openapi_client.json` are compared using `make sdk-overlay-create`, the diff is created 
which forms Speakeasy overlay. This overlay is saved in repo for CI, so that it can be applied on top of backend
`openapi.json` from the unstructured-api repo, when generating python client in Github Actions.
It can be also simulated locally using `make sdk-overlay-apply`
