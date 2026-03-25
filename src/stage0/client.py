"""Stage0 API client."""

import asyncio
import json

import httpx

from src.config import get_settings
from src.schemas.stage0 import Stage0Request, Stage0Response
from src.stage0.exceptions import (
    Stage0AuthorizationError,
    Stage0ConnectionError,
    Stage0TimeoutError,
)

settings = get_settings()


class Stage0Client:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = (base_url or settings.stage0_base_url).rstrip("/")
        self.api_key = api_key or settings.stage0_api_key
        self.timeout = timeout_seconds or settings.stage0_timeout_seconds
        # Shared client enables TCP connection reuse across requests.
        # When None, a per-request client is created as fallback.
        self._http_client = http_client

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

    async def _do_post(
        self,
        client: httpx.AsyncClient,
        url: str,
        payload: dict,
    ) -> httpx.Response:
        try:
            return await client.post(url, headers=self._headers(), json=payload)
        except httpx.TimeoutException as e:
            raise Stage0TimeoutError(f"Stage0 request timed out after {self.timeout}s") from e
        except httpx.RequestError as e:
            raise Stage0ConnectionError(f"Stage0 connection error: {e}") from e

    def _parse_response(self, response: httpx.Response) -> Stage0Response:
        if response.status_code >= 500:
            raise Stage0ConnectionError(f"Stage0 server error: HTTP {response.status_code}")

        if response.status_code >= 400:
            raise Stage0AuthorizationError(
                verdict="DENY",
                issues=[{"code": f"HTTP_{response.status_code}"}],
                request_id=None,
            )

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise Stage0ConnectionError(f"Stage0 returned invalid JSON: {e}") from e

        if "verdict" not in data:
            raise Stage0ConnectionError("Stage0 response missing required 'verdict' field")

        data["raw_response"] = data.copy()
        return Stage0Response(**data)

    async def check(self, request: Stage0Request) -> Stage0Response:
        url = f"{self.base_url}/check"
        payload = request.model_dump(exclude_none=True)

        if self._http_client is not None:
            response = await self._do_post(self._http_client, url, payload)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await self._do_post(client, url, payload)

        return self._parse_response(response)

    async def check_with_retry(
        self,
        request: Stage0Request,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> Stage0Response:
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                return await self.check(request)
            except Stage0TimeoutError as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)
            except Stage0ConnectionError as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)
            except Stage0AuthorizationError:
                raise

        raise last_error or Stage0ConnectionError("Unknown error after retries")

    def is_configured(self) -> bool:
        return bool(self.api_key)
