from __future__ import annotations

import functools
from typing import cast, Callable, Optional
from typing_extensions import ParamSpec
from urllib.parse import urlparse, urlunparse, ParseResult


_P = ParamSpec("_P")


def clean_server_url(func: Callable[_P, None]) -> Callable[_P, None]:

    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
        SERVER_URL_ARG_IDX = 3
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
                args = args[:SERVER_URL_ARG_IDX] + (urlunparse(cleaned_url),) + args[SERVER_URL_ARG_IDX+1:] # type: ignore
        
        return func(*args, **kwargs)

    return wrapper
