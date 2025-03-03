import pytest


@pytest.fixture(scope="module")
def platform_api_url():
    return "https://platform.unstructuredapp.io"


