from typing import Any, Optional, Dict
import logging
import requests
import json
from urllib.parse import urlparse
from uuid import uuid4

from .config import load_settings, get_env_or_setting

logger = logging.getLogger(__name__)


class WebhookClientError(RuntimeError):
    """
    Raised when the WebhookClient cannot perform an HTTP operation like
    network failure, timeout, invalid JSON, or unexpected status code.

    Stores extra context such as:
      - the HTTP method used (GET/POST)
      - the URL being accessed
      - the original exception if available
    """

    def __init__(
        self,
        message: str,
        method: Optional[str] = None,
        url: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ) -> None:
        
        self.method = method
        self.url = url
        self.original_exception = original_exception

        # Build a detailed message
        details = [message]

        if method:
            details.append(f"(method={method})")
        if url:
            details.append(f"(url={url})")
        if original_exception:
            details.append(f"(cause={original_exception!r})")

        full_message = " ".join(details)
        super().__init__(full_message)


class WebhookClient:
    """
    Client to interact with a Webhook.site endpoint.

    - Sends events to a capture URL (WEBHOOK_TARGET_URL)
    - Retrieves the latest captured request via Webhook.site API
    """

    def __init__(self, target_url: Optional[str] = None) -> None:
        settings = load_settings()
        webhook_cfg = settings.get("webhook", {})

        # Target URL where events are POSTed
        env_target_url = get_env_or_setting(
            "webhook.target_url",
            "WEBHOOK_TARGET_URL",
            default=None,
        )
        if target_url is not None:
            self.target_url = target_url
        elif env_target_url:
            self.target_url = env_target_url
        else:
            # setup error
            raise WebhookClientError(
                "Webhook target URL must be provided via argument or WEBHOOK_TARGET_URL env var."
            )

        # Base URL for the Webhook.site API (for retrieving requests)
        config_api_base = webhook_cfg.get("base_url", "https://webhook.site")
        env_api_base = get_env_or_setting(
            "webhook.api_base_url",
            "WEBHOOK_API_URL",
            default=config_api_base,
        )
        self.api_base_url = env_api_base.rstrip("/")

        logger.debug(
            "WebhookClient initialized with target_url=%s, api_base_url=%s",
            self.target_url,
            self.api_base_url,
        )

        # Optional API key for logged-in accounts (not needed for anonymous usage)
        self.api_key = get_env_or_setting(
            "webhook.api_key",
            "WEBHOOK_API_KEY",
            default=None,
        )

    def _extract_token_id(self) -> str:
        """
        Extract the tokenId from the target URL.
        Example:
            https://webhook.site/abcd1234  -> tokenId = 'abcd1234'
        """
        parsed_url = urlparse(self.target_url)
        segments = [seg for seg in parsed_url.path.split("/") if seg]
        if not segments:
            raise WebhookClientError(
                f"Could not extract tokenId from URL: {self.target_url}"
            )
        token_id = segments[0]

        logger.debug(
            "Extracted tokenId=%s from target_url=%s",
            token_id,
            self.target_url,
        )
        return token_id

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        # Webhook.site uses Api-Key for authenticated accounts
        if self.api_key:
            headers["Api-Key"] = self.api_key
        return headers

    def send_event(self, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Send a JSON payload to the webhook target URL via POST.
        """
        logger.info("Sending webhook event to %s", self.target_url)

        try:
            response = requests.post(self.target_url, json=payload, headers=headers)
        except requests.RequestException as exc:
            logger.error("Failed to send webhook event: %r", exc)
            raise WebhookClientError(
                "Failed to send webhook event",
                method="POST",
                url=self.target_url,
                original_exception=exc,
            ) from exc

        logger.info(
            "Webhook event POST -> %s (status %s)",
            response.url,
            response.status_code,
        )
        logger.debug("Webhook POST response body: %s", response.text)
        return response

    def retrieve_latest_request(self) -> Dict[str, Any]:
        """
        Fetch metadata for the latest request sent to this webhook URL using:
        GET {api_base_url}/token/{tokenId}/request/latest

        returns:
            - A dict with the request metadata if found.
            - An empty dict {} if there is no latest request yet (e.g. 404 status code returned).
        """
        token_id = self._extract_token_id()
        url = f"{self.api_base_url}/token/{token_id}/request/latest"
        headers = self._build_headers()

        logger.info("Fetching latest webhook request from %s", url)
        try:
            response = requests.get(url, headers=headers)
        except requests.RequestException as exc:
            logger.error("Failed to fetch latest webhook request: %r", exc)
            raise WebhookClientError(
                "Failed to fetch latest webhook request",
                method="GET",
                url=url,
                original_exception=exc,
            ) from exc

        # 404 is expected when there is no request yet so we treat it as "no data"
        if response.status_code == 404:
            logger.warning(
                "No latest webhook request found yet (404). Response body: %s",
                response.text,
            )
            return {}

        if response.status_code != 200:
            logger.error(
                "Unexpected status from webhook API: %s, body=%s",
                response.status_code,
                response.text,
            )
            raise WebhookClientError(
                "Unexpected status from webhook API",
                method="GET",
                url=url,
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode JSON from webhook API: %r", exc)
            raise WebhookClientError(
                "Failed to decode JSON from webhook API",
                method="GET",
                url=url,
                original_exception=exc,
            ) from exc

        logger.debug("Latest webhook request payload (metadata): %s", data)
        return data

    def retrieve_latest_request_content(self) -> Dict[str, Any]:
        """
        Retrieve latest request metadata and return the 'content' field as JSON
        (which is the original request body that was sent to the webhook URL).

        returns:
            - Parsed JSON dict if a request exists
            - {} if there is no content yet (no requests captured)
        """
        metadata = self.retrieve_latest_request()

        # If no metadata return empty dict
        if not metadata:
            logger.debug("No metadata returned for latest webhook request yet.")
            return {}

        content = metadata.get("content")

        if content is None:
            logger.warning("Latest webhook request has no 'content' field.")
            return {}

        try:
            # content is a JSON string, e.g: "{\"hello\":\"Rim\"}"
            body_json = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error(
                "Latest webhook request content is not valid JSON: %r",
                exc
            )
            raise WebhookClientError(
                "Latest webhook request content is not a valid JSON",
                original_exception=exc
            ) from exc

        logger.debug("Latest webhook request JSON body: %s", body_json)
        return body_json

