import pytest, logging
from utils.api_client import ApiClient
from utils.webhook_utils import WebhookClient

@pytest.fixture(scope="session")
def api_client() -> ApiClient:
    """
    Provides a shared ApiClient instance for all tests.
    requires REQRES_API_TOKEN to be set before running tests.
    """
    return ApiClient()

@pytest.fixture(scope="session")
def webhook_client() -> WebhookClient:
    """
    Provides a shared WebhookClient instance.
    Requires WEBHOOK_TARGET_URL to be set before running tests.
    """
    return WebhookClient()