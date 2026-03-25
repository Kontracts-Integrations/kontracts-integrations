"""
TRIRIGA SOAP client using zeep.
Supports real SOAP calls and demo/fixture mode.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level zeep client cache keyed by (base_url, username)
# Avoids re-downloading the WSDL on every request
_zeep_client_cache: Dict[Tuple[str, str], Any] = {}


class TririgaClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        wsdl_path: str = "/ws/TririgaWS?wsdl",
        demo_mode: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.wsdl_path = wsdl_path
        self.demo_mode = demo_mode or settings.demo_mode
        self._zeep_client = None

    def _get_wsdl_url(self) -> str:
        return f"{self.base_url}{self.wsdl_path}"

    def _get_zeep_client(self):
        cache_key = (self.base_url, self.username)
        if cache_key not in _zeep_client_cache:
            try:
                from zeep import Client
                from zeep.transports import Transport
                import requests
                import ssl
                from requests.adapters import HTTPAdapter
                from urllib3.util.ssl_ import create_urllib3_context

                session = requests.Session()
                session.auth = (self.username, self.password)
                if "techzone.ibm.com" in self.base_url or "https" in self.base_url:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                    # OpenSSL 3.x has SECLEVEL=1+ by default which blocks some IBM server
                    # cipher suites with a record-layer failure. Drop to SECLEVEL=0 to allow all.
                    class _LaxSSLAdapter(HTTPAdapter):
                        def init_poolmanager(self, *args, **kwargs):
                            ctx = create_urllib3_context()
                            ctx.check_hostname = False
                            ctx.verify_mode = ssl.CERT_NONE
                            try:
                                ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
                            except ssl.SSLError:
                                pass
                            kwargs["ssl_context"] = ctx
                            super().init_poolmanager(*args, **kwargs)

                        def proxy_manager_for(self, proxy, **proxy_kwargs):
                            ctx = create_urllib3_context()
                            ctx.check_hostname = False
                            ctx.verify_mode = ssl.CERT_NONE
                            try:
                                ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
                            except ssl.SSLError:
                                pass
                            proxy_kwargs["ssl_context"] = ctx
                            return super().proxy_manager_for(proxy, **proxy_kwargs)

                    session.mount("https://", _LaxSSLAdapter())
                    session.verify = False

                transport = Transport(session=session, timeout=30)
                _zeep_client_cache[cache_key] = Client(
                    wsdl=self._get_wsdl_url(), transport=transport
                )
                logger.info(f"Initialized zeep client for {self.base_url}")
            except Exception as e:
                logger.error(f"Failed to initialize zeep client: {e}")
                raise
        return _zeep_client_cache[cache_key]

    async def test_connection(self) -> Tuple[bool, str, Optional[Dict]]:
        if self.demo_mode:
            return True, "Demo mode — connection simulated successfully", {
                "mode": "demo",
                "wsdl_url": self._get_wsdl_url(),
            }
        try:
            loop = asyncio.get_event_loop()
            client = await loop.run_in_executor(None, self._get_zeep_client)
            info = await loop.run_in_executor(
                None, lambda: client.service.getApplicationInfo()
            )
            from app.tririga_client.normalizer import normalize_soap_response
            details = normalize_soap_response(info)
            if not isinstance(details, dict):
                details = {"result": details}
            return True, "Connection successful", details
        except Exception as e:
            logger.warning(f"TRIRIGA connection test failed: {e}")
            return False, str(e), None

    async def get_modules(self) -> List[Dict[str, Any]]:
        if self.demo_mode:
            from app.tririga_client.fixtures import DEMO_MODULES
            return DEMO_MODULES

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)
            result = await loop.run_in_executor(
                None,
                lambda: client.service.getModules(),
            )
            from app.tririga_client.normalizer import normalize_soap_response
            normalized = normalize_soap_response(result)
            if isinstance(normalized, list):
                return normalized
            return normalized.get("modules", normalized.get("item", [normalized]))
        except Exception as e:
            logger.error(f"getModules failed: {e}")
            raise

    async def get_business_objects(
        self, module_name: str, is_stand_alone: bool = True
    ) -> List[Dict[str, Any]]:
        if self.demo_mode:
            from app.tririga_client.fixtures import get_demo_business_objects
            return get_demo_business_objects(module_name)

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)
            result = await loop.run_in_executor(
                None,
                lambda: client.service.getObjectTypeListByModuleName(
                    moduleName=module_name,
                    isStandAlone=is_stand_alone,
                ),
            )
            from app.tririga_client.normalizer import normalize_soap_response
            normalized = normalize_soap_response(result)
            items = []
            if isinstance(normalized, list):
                items = normalized
            elif isinstance(normalized, dict):
                for key in ("out", "BaseObjectType", "item", "result"):
                    if key in normalized:
                        val = normalized[key]
                        items = val if isinstance(val, list) else [val]
                        break
                if not items:
                    items = [normalized]
            return [
                {
                    "name": str(item.get("name", item)) if isinstance(item, dict) else str(item),
                    "label": str(item.get("name", item)) if isinstance(item, dict) else str(item),
                    "id": item.get("id") if isinstance(item, dict) else None,
                }
                for item in items
                if item
            ]
        except Exception as e:
            logger.error(f"getObjectTypeListByModuleName failed for {module_name}: {e}")
            raise

    async def get_module_fields(
        self, module_name: str, object_type_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if self.demo_mode:
            from app.tririga_client.fixtures import get_demo_fields
            return get_demo_fields(object_type_name or module_name)

        object_type_name = object_type_name or module_name
        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)
            result = await loop.run_in_executor(
                None,
                lambda: client.service.getObjectTypeByName(
                    moduleName=module_name,
                    objectTypeName=object_type_name,
                ),
            )
            from app.tririga_client.normalizer import normalize_soap_response, extract_fields
            normalized = normalize_soap_response(result)
            return extract_fields(normalized)
        except Exception as e:
            logger.error(f"getObjectTypeByName failed for {module_name}/{object_type_name}: {e}")
            raise

    async def run_named_query(
        self,
        module_name: str,
        query_name: str,
        filters: Dict[str, Any],
        max_records: int = 100,
    ) -> List[Dict[str, Any]]:
        if self.demo_mode:
            from app.tririga_client.fixtures import get_demo_records
            return get_demo_records(module_name, query_name, max_records)

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)

            # Build filter string from dict
            filter_str = ""
            if filters:
                parts = []
                for key, val in filters.items():
                    parts.append(f"{key}={val}")
                filter_str = "&".join(parts)

            result = await loop.run_in_executor(
                None,
                lambda: client.service.runNamedQuery(
                    moduleName=module_name,
                    queryName=query_name,
                    filterCondition=filter_str,
                    pageNumber=1,
                    pageSize=max_records,
                ),
            )
            from app.tririga_client.normalizer import normalize_query_response
            return normalize_query_response(result)
        except Exception as e:
            logger.error(f"runNamedQuery failed for {module_name}/{query_name}: {e}")
            raise

    async def get_record(self, spec_id: int, record_id: int) -> Dict[str, Any]:
        if self.demo_mode:
            from app.tririga_client.fixtures import DEMO_RECORD
            return DEMO_RECORD

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)
            result = await loop.run_in_executor(
                None,
                lambda: client.service.getRecordDataHeaders(
                    specId=spec_id,
                    recordId=record_id,
                ),
            )
            from app.tririga_client.normalizer import normalize_soap_response
            return normalize_soap_response(result)
        except Exception as e:
            logger.error(f"getRecordDataHeaders failed for {spec_id}/{record_id}: {e}")
            raise

    async def save_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.demo_mode:
            return {"success": True, "recordId": "DEMO-001", "specId": "12345"}

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)
            result = await loop.run_in_executor(
                None,
                lambda: client.service.saveRecord(
                    tririgaWS=record_data,
                ),
            )
            from app.tririga_client.normalizer import normalize_soap_response
            return normalize_soap_response(result)
        except Exception as e:
            logger.error(f"saveRecord failed: {e}")
            raise

    async def get_wsdl_structure(self) -> Dict[str, Any]:
        if self.demo_mode:
            from app.tririga_client.fixtures import DEMO_WSDL_STRUCTURE
            return DEMO_WSDL_STRUCTURE

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)
            from app.tririga_client.wsdl_parser import extract_wsdl_structure
            structure = await loop.run_in_executor(
                None, lambda: extract_wsdl_structure(client)
            )
            return structure
        except Exception as e:
            logger.error(f"WSDL parsing failed: {e}")
            raise
