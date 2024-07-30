from typing import Optional, Tuple, Union

import logging
import requests

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.types import AfterErrorContext, AfterErrorHook

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


class SuggestDefiningUrlIf401AfterErrorHook(AfterErrorHook):
    """Hook advising users to check that 'server_url' is defined if a 401 error is encountered."""

    def warn_if_401(self, response: Optional[requests.Response]):
        """If the paid API returns 401, warn the user in case they meant to use the free api."""
        if response is not None and response.status_code == 401:
            logger.warning(
                "This API key is invalid against the paid API. If intending to use the free API, please initialize UnstructuredClient with `server='free-api'`."
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
