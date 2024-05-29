from .clean_server_url_hook import CleanServerUrlSDKInitHook
from .log_retries_after_error_hook import LogRetriesAfterErrorHook
from .suggest_defining_url import SuggestDefiningUrlIf401AfterErrorHook
from .split_pdf_hook import SplitPdfHook
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
