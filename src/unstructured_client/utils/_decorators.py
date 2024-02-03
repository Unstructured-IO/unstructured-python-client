from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Dict, Optional
from typing_extensions import ParamSpec, Concatenate
from urllib.parse import urlparse, urlunparse, ParseResult


_P = ParamSpec("_P")


def clean_server_url(func: Callable[_P, None]) -> Callable[_P, None]:

    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:

        def get_call_args_applying_defaults() -> Dict[str, Any]:
            """Map both explicit and default arguments of decorated func call by param name."""
            sig = inspect.signature(func)
            call_args: Dict[str, Any] = dict(
                **dict(zip(sig.parameters, args)), **kwargs
            )
            for param in sig.parameters.values():
                if param.name not in call_args and param.default is not param.empty:
                    call_args[param.name] = param.default
            return call_args

        call_args = get_call_args_applying_defaults()

        server_url: Optional[str] = call_args.get("server_url")

        if server_url:
            # -- add a url scheme if not present (urllib.parse does not work reliably without it)
            if "http" not in server_url:
                server_url = "http://" + server_url

            parsed_url: ParseResult = urlparse(server_url)

            if "api.unstructuredapp.io" in server_url:
                if parsed_url.scheme != "https":
                    parsed_url = parsed_url._replace(scheme="https")
            else:
                # -- if not a paid api url, assume the api is hosted locally and the scheme is "http"
                if parsed_url.scheme != "http":
                    parsed_url = parsed_url._replace(scheme="http")

            # -- path should always be empty
            cleaned_url = parsed_url._replace(path="")
            call_args["server_url"] = urlunparse(cleaned_url)

        # -- call_args contains all args and kwargs. If users define some parameters using
        # -- kwargs, param definitions would be duplicated. Pass only the `self`
        # -- param as an arg and keep the rest in kwargs to prevent duplicates.
        self_arg = (call_args.pop("self"),)
        
        return func(*self_arg, **call_args) # type: ignore

    return wrapper
