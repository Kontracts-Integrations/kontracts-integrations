"""
TRIRIGA SOAP client using zeep.
Supports real SOAP calls and demo/fixture mode.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


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
        if self._zeep_client is None:
            try:
                from zeep import Client
                from zeep.transports import Transport
                import requests

                session = requests.Session()
                session.auth = (self.username, self.password)
                transport = Transport(session=session, timeout=30)
                self._zeep_client = Client(
                    wsdl=self._get_wsdl_url(), transport=transport
                )
            except Exception as e:
                logger.error(f"Failed to initialize zeep client: {e}")
                raise
        return self._zeep_client

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
                lambda: client.service.getModules(
                    username=self.username, password=self.password
                ),
            )
            from app.tririga_client.normalizer import normalize_soap_response
            normalized = normalize_soap_response(result)
            if isinstance(normalized, list):
                return normalized
            return normalized.get("modules", normalized.get("item", [normalized]))
        except Exception as e:
            logger.error(f"getModules failed: {e}")
            raise

    async def get_module_fields(self, module_name: str) -> List[Dict[str, Any]]:
        if self.demo_mode:
            from app.tririga_client.fixtures import get_demo_fields
            return get_demo_fields(module_name)

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)
            result = await loop.run_in_executor(
                None,
                lambda: client.service.getObjectTypeByName(
                    username=self.username,
                    password=self.password,
                    moduleName=module_name,
                ),
            )
            from app.tririga_client.normalizer import normalize_soap_response, extract_fields
            normalized = normalize_soap_response(result)
            return extract_fields(normalized)
        except Exception as e:
            logger.error(f"getObjectTypeByName failed for {module_name}: {e}")
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
                    username=self.username,
                    password=self.password,
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
                    username=self.username,
                    password=self.password,
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
                    username=self.username,
                    password=self.password,
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
