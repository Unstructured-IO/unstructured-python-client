"""Registration of custom, human-written hooks."""

from .custom import (
    CleanServerUrlSDKInitHook,
    LoggerHook,
    SplitPdfHook,
)
from .types import Hooks


# This file is only ever generated once on the first generation and then is free to be modified.
# Any hooks you wish to add should be registered in the init_hooks function. Feel free to define
# them in this file or in separate files in the hooks folder.


def init_hooks(hooks: Hooks):
    # pylint: disable=unused-argument
    """Add hooks by calling `hooks.register_<type_or>_hook` with an instance of that hook.

    Hooks are registered per SDK instance, and are valid for the lifetime of the SDK instance
    """

    # Initialize custom hooks
    clean_server_url_hook = CleanServerUrlSDKInitHook()
    logger_hook = LoggerHook()
    split_pdf_hook = SplitPdfHook()

    # NOTE: logger_hook should stay registered last as logs the status of
    # request and whether it will be retried which can be changed by e.g. split_pdf_hook

    # Register SDK Init hooks
    hooks.register_sdk_init_hook(clean_server_url_hook)
    hooks.register_sdk_init_hook(logger_hook)
    hooks.register_sdk_init_hook(split_pdf_hook)

    # Register Before Request hooks
    hooks.register_before_request_hook(split_pdf_hook)

    # Register After Error hooks
    hooks.register_after_success_hook(split_pdf_hook)
    hooks.register_after_success_hook(logger_hook)

    # Register After Error hooks
    hooks.register_after_error_hook(split_pdf_hook)
    hooks.register_after_error_hook(logger_hook)  
