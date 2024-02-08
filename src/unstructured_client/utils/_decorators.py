from __future__ import annotations

import functools
from typing import cast, Callable, TYPE_CHECKING, Optional
from typing_extensions import ParamSpec
from urllib.parse import urlparse, urlunparse, ParseResult
import warnings

from unstructured_client.models import errors, operations

if TYPE_CHECKING:
    from unstructured_client.general import General


_P = ParamSpec("_P")
SERVER_URL_ARG_IDX = 3


def clean_server_url(func: Callable[_P, None]) -> Callable[_P, None]:
    """A decorator for fixing common types of malformed 'server_url' arguments.

    This decorator addresses the common problem of users omitting or using the wrong url scheme
    and/or adding the '/general/v0/general' path to the 'server_url'. The decorator should be
    manually applied to the __init__ method of UnstructuredClient after merging a PR from Speakeasy.
    """

    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
        url_is_in_kwargs = True

        server_url: Optional[str] = cast(Optional[str], kwargs.get("server_url"))

        if server_url is None and len(args) > SERVER_URL_ARG_IDX:
            server_url = cast(str, args[SERVER_URL_ARG_IDX])
            url_is_in_kwargs = False

        if server_url:
            # -- add a url scheme if not present (urllib.parse does not work reliably without it)
            if "http" not in server_url:
                server_url = "http://" + server_url

            parsed_url: ParseResult = urlparse(server_url)

            if "api.unstructuredapp.io" in server_url:
                if parsed_url.scheme != "https":
                    parsed_url = parsed_url._replace(scheme="https")

            # -- path should always be empty
            cleaned_url = parsed_url._replace(path="")

            if url_is_in_kwargs:
                kwargs["server_url"] = urlunparse(cleaned_url)
            else:
                args = (
                    args[:SERVER_URL_ARG_IDX]
                    + (urlunparse(cleaned_url),)
                    + args[SERVER_URL_ARG_IDX + 1 :]
                )  # type: ignore

        return func(*args, **kwargs)

    return wrapper


def suggest_defining_url_if_401(
    func: Callable[_P, operations.PartitionResponse]
) -> Callable[_P, operations.PartitionResponse]:
    """A decorator to suggest defining the 'server_url' parameter if a 401 Unauthorized error is
    encountered.

    This decorator addresses the common problem of users not passing in the 'server_url' when
    using their paid api key. The decorator should be manually applied to General.partition after
    merging a PR from Speakeasy.
    """

    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> operations.PartitionResponse:
        try:
            return func(*args, **kwargs)
        except errors.SDKError as error:
            if error.status_code == 401:
                general_obj: General = args[0]  # type: ignore
                if not general_obj.sdk_configuration.server_url:
                    warnings.warn(
                        "If intending to use the paid API, please define `server_url` in your request."
                    )

            return func(*args, **kwargs)

    return wrapper
