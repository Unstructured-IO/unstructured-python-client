from typing import Optional, Tuple, Union
import warnings

import requests

from unstructured_client._hooks.types import AfterErrorContext, AfterErrorHook


class SuggestDefiningUrlIf401AfterErrorHook(AfterErrorHook):
    """Hook advising users to check that 'server_url' is defined if a 401 error is encountered."""

    def warn_if_401(self, response: Optional[requests.Response]):
        """Suggest defining 'server_url' if a 401 error is encountered."""
        if response is not None and response.status_code == 401:
            warnings.warn(
                "If intending to use the paid API, please define `server_url` in your request."
            )

    def after_error(
        self,
        hook_ctx: AfterErrorContext,
        response: Optional[requests.Response],
        error: Optional[Exception],
    ) -> Union[Tuple[Optional[requests.Response], Optional[Exception]], Exception]:
        """Concrete implementation for AfterErrorHook."""
        self.warn_if_401(response)
        return response, error
