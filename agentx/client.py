"""Exchange SDK — buyer interface. One method: call()."""

from __future__ import annotations
import httpx
from agentx.types import CallRequest, ExchangeResult


class Exchange:
    """Developer-facing exchange client.

    Usage:
        ex = Exchange(api_key="ax_live_...")
        result = ex.call(capability="ocr", input="...", max_price=5.0)
        print(result.output, result.price_cents, result.agent_id)
    """

    def __init__(self, api_key: str = "demo",
                 server_url: str = "http://localhost:8000"):
        if not api_key:
            raise ValueError("api_key is required")
        if not server_url:
            raise ValueError("server_url is required")
        self.api_key = api_key
        self.server_url = server_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def call(self, capability: str, input: str,
             max_price: float, min_quality: int = 6,
             timeout: float = 30.0) -> ExchangeResult:
        """Submit a task to the exchange. Returns the winning result.

        Args:
            capability: What kind of work (e.g., "ocr", "legal", "code")
            input: The actual task/input data
            max_price: Maximum price in USD you're willing to pay
            min_quality: Minimum quality score (1-10), default 6
            timeout: Max seconds to wait for a result

        Returns:
            ExchangeResult with output, agent_id, price, score

        Raises:
            ValueError: No agents available, or invalid parameters
            TimeoutError: No result within timeout
            ConnectionError: Can't reach the exchange server
            RuntimeError: Server returned an unexpected error
        """
        # Pydantic validates constraints (min_length, gt=0, etc.)
        req = CallRequest(
            capability=capability,
            input=input,
            max_price=max_price,
            min_quality=min_quality,
            timeout=timeout,
        )

        try:
            with httpx.Client(timeout=timeout + 10.0) as client:
                resp = client.post(
                    f"{self.server_url}/call",
                    json=req.model_dump(),
                    headers=self._headers,
                )
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to exchange at {self.server_url}"
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request timed out after {timeout}s"
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error: {e}")

        if resp.status_code == 401:
            raise PermissionError("Invalid API key")
        if resp.status_code == 404:
            detail = resp.json().get("detail", "No agents available")
            raise ValueError(detail)
        if resp.status_code == 504:
            detail = resp.json().get("detail", "Request timed out")
            raise TimeoutError(detail)
        if resp.status_code == 422:
            detail = resp.json().get("detail", "Invalid request")
            raise ValueError(f"Validation error: {detail}")
        if resp.status_code >= 500:
            raise RuntimeError(
                f"Exchange server error ({resp.status_code}): {resp.text[:200]}"
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Unexpected response ({resp.status_code}): {resp.text[:200]}"
            )

        try:
            return ExchangeResult(**resp.json())
        except Exception as e:
            raise RuntimeError(f"Invalid response from exchange: {e}")
