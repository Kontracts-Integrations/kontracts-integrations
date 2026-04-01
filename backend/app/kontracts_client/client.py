"""
HTTP client for the Kontracts REST API.
Handles Auth0 client credentials OAuth2 flow.
"""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Module-level token cache: keyed by (client_id, audience) → (access_token, expires_at)
# Shared across all KontractsClient instances so tokens survive request boundaries.
_TOKEN_CACHE: Dict[Tuple[str, str], Tuple[str, float]] = {}

_DEMO_LEASES = [
    {
        "id": "lease_001",
        "name": "HQ Office Lease - New York",
        "lease_type": "operating",
        "commencement_date": "2020-01-01",
        "expiration_date": "2025-12-31",
        "monthly_payment": 75000.00,
        "currency": "USD",
        "status": "active",
    },
    {
        "id": "lease_002",
        "name": "Chicago Data Center Lease",
        "lease_type": "finance",
        "commencement_date": "2019-07-01",
        "expiration_date": "2029-06-30",
        "monthly_payment": 45000.00,
        "currency": "USD",
        "status": "active",
    },
]


class KontractsClient:
    def __init__(
        self,
        base_url: str,
        auth0_domain: str,
        client_id: str,
        client_secret: str,
        audience: str,
        demo_mode: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth0_domain = auth0_domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.audience = audience
        self.demo_mode = demo_mode

    async def _get_access_token(self) -> str:
        cache_key = (self.client_id, self.audience)
        cached = _TOKEN_CACHE.get(cache_key)
        if cached:
            token, expires_at = cached
            if time.time() < expires_at - 60:
                return token

        if not self.auth0_domain:
            raise ValueError("Auth0 domain is not configured. Please update the connection with a valid Auth0 domain.")
        domain = self.auth0_domain.removeprefix("https://").removeprefix("http://").rstrip("/")
        token_url = f"https://{domain}/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
        }

        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(token_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        access_token = data["access_token"]
        expires_in = data.get("expires_in", 86400)
        expires_at = time.time() + expires_in
        _TOKEN_CACHE[cache_key] = (access_token, expires_at)
        logger.debug("Auth0 token refreshed for client_id=%s, expires_in=%ss", self.client_id, expires_in)
        return access_token

    async def _headers(self) -> Dict[str, str]:
        token = await self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.get(
                f"{self.base_url}{path}", headers=headers, params=params
            )
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, data: Dict) -> Any:
        headers = await self._headers()
        logger.info("POST %s payload: %s", path, data)
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                f"{self.base_url}{path}", headers=headers, json=data
            )
            if resp.is_error:
                logger.error(
                    "POST %s → %s: %s", path, resp.status_code, resp.text
                )
            resp.raise_for_status()
            return resp.json()

    async def _put(self, path: str, data: Dict) -> Any:
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.put(
                f"{self.base_url}{path}", headers=headers, json=data
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self) -> Tuple[bool, str, Optional[Dict]]:
        if self.demo_mode:
            return True, "Demo mode — Kontracts connection simulated", {
                "mode": "demo",
                "base_url": self.base_url,
            }
        try:
            health = await self.health_check()
            return True, "Connection successful", health
        except Exception as e:
            return False, str(e), None

    async def health_check(self) -> Dict[str, Any]:
        if self.demo_mode:
            return {"status": "healthy", "version": "demo"}
        return await self._get("/health")

    async def get_openapi_schema(self) -> Dict[str, Any]:
        if self.demo_mode:
            from app.kontracts_client.schema_parser import DEMO_OPENAPI_SCHEMA
            return DEMO_OPENAPI_SCHEMA
        return await self._get("/openapi.json")

    async def list_leases(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        if self.demo_mode:
            return {
                "results": _DEMO_LEASES,
                "count": len(_DEMO_LEASES),
                "page": page,
                "page_size": page_size,
            }
        return await self._get(
            "/api/v1/leases/", params={"page": page, "page_size": page_size}
        )

    async def create_lease(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.demo_mode:
            return {"id": "demo_lease_001", **payload}
        return await self._post("/api/v1/leases/", payload)

    async def update_lease(
        self, lease_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self.demo_mode:
            return {"id": lease_id, **payload}
        return await self._put(f"/api/v1/leases/{lease_id}", payload)

    async def get_lease(self, lease_id: str) -> Dict[str, Any]:
        if self.demo_mode:
            return next(
                (l for l in _DEMO_LEASES if l["id"] == lease_id),
                {"id": lease_id},
            )
        return await self._get(f"/api/v1/leases/{lease_id}")

    async def create_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.demo_mode:
            return {"id": "demo_payment_001", **payload}
        return await self._post("/api/v1/payments/", payload)

    async def list_currencies(self) -> List[Dict[str, Any]]:
        if self.demo_mode:
            return [
                {"code": "USD", "name": "US Dollar"},
                {"code": "EUR", "name": "Euro"},
                {"code": "GBP", "name": "British Pound"},
                {"code": "CAD", "name": "Canadian Dollar"},
            ]
        result = await self._get("/api/v1/currencies/")
        return result if isinstance(result, list) else result.get("results", [])

    async def push_record(
        self, endpoint: str, method: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generic push to any Kontracts endpoint."""
        if self.demo_mode:
            return {"id": "demo_001", "status": "created", **payload}

        method = method.upper()
        if method == "POST":
            return await self._post(endpoint, payload)
        elif method in ("PUT", "PATCH"):
            return await self._put(endpoint, payload)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
