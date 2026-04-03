"""Exchange SDK — buyer interface. One method: call()."""

from __future__ import annotations
import httpx
from bazaar.types import LLMConfig, ExchangeConfig, CallRequest, ExchangeResult


class Exchange:
    """Developer-facing exchange client.

    Usage:
        ex = Exchange(api_key="ax_live_...")
        result = ex.call(
            llm={"input": "Write a haiku about the ocean"},
            exchange={"max_price": 0.05},
        )
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

    def call(self, llm: dict, exchange: dict) -> ExchangeResult | list[ExchangeResult]:
        """Submit a task to the exchange. Returns the winning result(s).

        Args:
            llm: LLM parameters (identical to OpenAI's API).
                Required: input
                Optional: instructions, response_format, max_tokens,
                    temperature, top_p, stream, attachments

            exchange: Exchange parameters (what makes Bazaar different).
                Required: max_price
                Optional: top_n (default 1), min_quality,
                    quality_criteria, judge, timeout, metadata

        Returns:
            ExchangeResult for top_n=1, list[ExchangeResult] for top_n>1.

        Raises:
            ValueError: Invalid parameters or missing required fields.
            TimeoutError: No result within timeout.
            ConnectionError: Can't reach the exchange server.
            RuntimeError: Server returned an unexpected error.
        """
        # Validate response_format if provided
        rf = llm.get("response_format")
        if rf is not None:
            fmt_type = rf.get("type") if isinstance(rf, dict) else None
            if fmt_type not in ("text", "json_schema"):
                raise ValueError(
                    "response_format['type'] must be 'text' or 'json_schema'"
                )
            if fmt_type == "json_schema" and "json_schema" not in rf:
                raise ValueError(
                    "response_format must include 'json_schema' "
                    "when type is 'json_schema'"
                )

        req = CallRequest(
            llm=LLMConfig(**llm),
            exchange=ExchangeConfig(**exchange),
        )

        timeout = req.exchange.timeout
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
            data = resp.json()
            if isinstance(data, list):
                results = [ExchangeResult(**r) for r in data]
                return results[0] if len(results) == 1 else results
            return ExchangeResult(**data)
        except Exception as e:
            raise RuntimeError(f"Invalid response from exchange: {e}")
