from typing import Any, Dict, Optional
import logging
import time

import requests

from .config import load_settings, get_env_or_setting

logger = logging.getLogger(__name__)


class ApiClientError(RuntimeError):
    """
    Raised when the ApiClient cannot successfully execute an HTTP request
    due to network/transport issues (e.g., timeouts, connection errors).

    Stores extra context:
      - HTTP method (GET/POST/DELETE/...)
      - URL being accessed
      - original exception, if any
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

        details = [message]
        if method:
            details.append(f"(method={method})")
        if url:
            details.append(f"(url={url})")
        if original_exception:
            details.append(f"(cause={original_exception!r})")

        full_message = " ".join(details)
        super().__init__(full_message)


class ApiClient:
    """
    API client for the Reqres API.

    - Base URL comes from config/settings.yaml (api.base_url)
    - API token comes from env var REQRES_API_TOKEN, with optional fallback
      to api.token in settings (for local debugging), sent as `x-api-key`.
    - All requests share a default timeout, configurable in config/settings.yaml
    """

    def __init__(self, base_url: Optional[str] = None) -> None:
        settings = load_settings()
        api_cfg = settings.get("api", {})

        config_base_url = api_cfg.get("base_url")
        token = get_env_or_setting("api.token", "REQRES_API_TOKEN", default=None)

        # self.base_url
        if base_url is not None:
            self.base_url = base_url.rstrip("/")  # remove trailing '/'
        elif config_base_url:
            self.base_url = config_base_url.rstrip("/")
        else:
            raise ValueError(
                "API base URL must be provided either via class argument "
                "or in config/settings.yaml under api.base_url."
            )

        # self.default_headers
        self.default_headers: Dict[str, str] = {
            "Accept": "application/json",
        }
        if token:
            # Reqres expects the API key in this header: x-api-key
            self.default_headers["x-api-key"] = token
        else:
            raise ValueError(
                "API token must be provided, ideally via the REQRES_API_TOKEN "
                "environment variable or config/settings.yaml under api.token."
            )

        # self.default_timeout (value for all requests)
        timeout_value = api_cfg.get("timeout")
        try:
            self.default_timeout: float = float(timeout_value)
        except (TypeError, ValueError):
            self.default_timeout = 10.0

        logger.debug(
            "ApiClient initialized with base_url=%s, has_token=%s, timeout=%s",
            self.base_url,
            bool(token),
            self.default_timeout
        )

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _merge_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """
        Merge per-call headers with default headers.
        Per-call headers win in case of conflict.
        """
        merged = dict(self.default_headers)
        if headers:
            merged.update(headers)
        return merged

    def _request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any
    ) -> requests.Response:
        """
        Helper that performs HTTP requests with logging and error handling.

        Args:
            method: HTTP method name (GET, POST, DELETE, ...)
            path: endpoint path
            headers: optional per-call headers
            timeout: optional per-call timeout
        """
        url = self._build_url(path)
        merged_headers = self._merge_headers(headers)
        effective_timeout = timeout or self.default_timeout

        logger.info("HTTP %s %s", method.upper(), url)
        logger.debug("Request headers: %s", merged_headers)
        if "json" in kwargs:
            logger.debug("Request JSON payload: %s", kwargs["json"])

        start = time.time()
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=merged_headers,
                timeout=effective_timeout,
                **kwargs,
            )
        except requests.exceptions.RequestException as exc:
            elapsed = time.time() - start
            logger.error(
                "HTTP %s %s failed after %.3fs: %r",
                method.upper(),
                url,
                elapsed,
                exc,
            )
            # Wrap low-level network errors in ApiClientError
            raise ApiClientError(
                "HTTP request failed",
                method=method.upper(),
                url=url,
                original_exception=exc,
            ) from exc

        elapsed = time.time() - start
        logger.info(
            "HTTP %s %s -> %s (%.3fs)",
            method.upper(),
            url,
            response.status_code,
            elapsed,
        )

        return response

    def get(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any
    ) -> requests.Response:
        return self._request("GET", path, headers=headers, timeout=timeout, **kwargs)

    def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> requests.Response:
        return self._request(
            "POST",
            path,
            headers=headers,
            timeout=timeout,
            json=json,
            **kwargs
        )

    def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any
    ) -> requests.Response:
        return self._request("DELETE", path, headers=headers, timeout=timeout, **kwargs)
