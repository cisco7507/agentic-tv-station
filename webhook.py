import os
import logging
import json
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Base exception for webhook errors."""
    pass


class WebhookTimeoutError(WebhookError):
    """Raised when webhook request times out."""
    pass


class WebhookResponseError(WebhookError):
    """Raised when webhook returns non-2xx response."""
    pass


class WebhookClient:
    """HTTP webhook client for making API requests."""
    
    def __init__(
        self,
        timeout: int = 30,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        self.timeout = timeout
        self.default_headers = default_headers or {}
    
    def _build_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgenticTVStation/1.0",
        }
        headers.update(self.default_headers)
        if additional_headers:
            headers.update(additional_headers)
        return headers
    
    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> dict:
        """Send POST request to webhook URL.
        
        Args:
            url: Target webhook URL
            data: JSON payload
            additional_headers: Additional headers
            
        Returns:
            Dictionary with response metadata
        """
        body = json.dumps(data).encode("utf-8") if data else None
        request = Request(
            url,
            data=body,
            headers=self._build_headers(headers),
            method="POST",
        )
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_body = response.read().decode("utf-8")
                return {
                    "status_code": response.status,
                    "body": response_body,
                    "success": True,
                }
        except URLError as e:
            if isinstance(e.reason, str) and "timed out" in e.reason.lower():
                raise WebhookTimeoutError(f"Request timed out: {url}") from e
            raise WebhookError(f"Request failed: {e}") from e
    
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> dict:
        """Send GET request to URL.
        
        Args:
            url: Target URL
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Dictionary with response metadata
        """
        if params:
            url = f"{url}?{urlencode(params)}"
        
        request = Request(
            url,
            headers=self._build_headers(headers),
            method="GET",
        )
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_body = response.read().decode("utf-8")
                return {
                    "status_code": response.status,
                    "body": response_body,
                    "success": True,
                }
        except URLError as e:
            raise WebhookError(f"Request failed: {e}") from e
    
    def put(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> dict:
        """Send PUT request to URL."""
        body = json.dumps(data).encode("utf-8") if data else None
        request = Request(
            url,
            data=body,
            headers=self._build_headers(headers),
            method="PUT",
        )
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_body = response.read().decode("utf-8")
                return {
                    "status_code": response.status,
                    "body": response_body,
                    "success": True,
                }
        except URLError as e:
            raise WebhookError(f"Request failed: {e}") from e
