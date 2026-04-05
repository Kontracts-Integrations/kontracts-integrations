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

            # Unwrap zeep's "out" envelope and other common wrappers
            items = []
            if isinstance(normalized, list):
                items = normalized
            elif isinstance(normalized, dict):
                for key in ("out", "modules", "item", "result"):
                    if key in normalized:
                        val = normalized[key]
                        items = val if isinstance(val, list) else [val]
                        break
                if not items:
                    items = [normalized]

            # Normalize each item to {name, label, id} so the frontend can render it
            return [
                {
                    "name": str(item.get("name", item)) if isinstance(item, dict) else str(item),
                    "label": str(item.get("label", item.get("name", item))) if isinstance(item, dict) else str(item),
                    "id": item.get("id") if isinstance(item, dict) else None,
                }
                for item in items
                if item
            ]
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

    async def get_associated_objects(
        self, object_type_id: int
    ) -> List[Dict[str, Any]]:
        if self.demo_mode:
            from app.tririga_client.fixtures import get_demo_associated_objects
            return get_demo_associated_objects(object_type_id)

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)
            result = await loop.run_in_executor(
                None,
                lambda: client.service.getAssociationDefinitions(
                    objectTypeId=object_type_id,
                ),
            )
            from app.tririga_client.normalizer import normalize_soap_response
            normalized = normalize_soap_response(result)

            # Unwrap "out" envelope
            if isinstance(normalized, dict) and "out" in normalized:
                normalized = normalized["out"]

            # Build module ID → name map to resolve associatedModuleId
            modules = await self.get_modules()
            module_id_map = {
                m["id"]: m["name"]
                for m in modules
                if isinstance(m.get("id"), int)
            }

            # Normalise to list of AssociationDefinition items
            if isinstance(normalized, dict):
                items = normalized.get("AssociationDefinition", normalized.get("item", []))
            elif isinstance(normalized, list):
                items = normalized
            else:
                items = [normalized] if normalized else []
            if not isinstance(items, list):
                items = [items]

            # Collect unique (module_id, module_name) pairs from items
            module_id_to_name: dict = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                mid = item.get("associatedModuleId")
                if mid is not None and mid not in module_id_to_name:
                    module_id_to_name[mid] = module_id_map.get(mid, str(mid)).strip()

            # Resolve associatedObjectTypeId → object type name for each module in parallel
            async def _fetch_bo_id_map(module_name: str) -> dict:
                try:
                    bos = await self.get_business_objects(module_name, is_stand_alone=False)
                    return {bo["id"]: bo["name"] for bo in bos if bo.get("id") is not None}
                except Exception:
                    return {}

            bo_id_maps: dict = {}  # {module_id: {obj_type_id: obj_type_name}}
            tasks = {
                mid: _fetch_bo_id_map(mname)
                for mid, mname in module_id_to_name.items()
                if mname
            }
            fetched = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for mid, result_or_exc in zip(tasks.keys(), fetched):
                bo_id_maps[mid] = result_or_exc if isinstance(result_or_exc, dict) else {}

            results = []
            seen = set()
            for item in items:
                if not isinstance(item, dict):
                    continue
                assoc_name = item.get("associationName") or ""
                assoc_module_id = item.get("associatedModuleId")
                assoc_obj_type_id = item.get("associatedObjectTypeId")
                assoc_module = module_id_to_name.get(assoc_module_id, str(assoc_module_id) if assoc_module_id is not None else "")
                obj_type_name = bo_id_maps.get(assoc_module_id, {}).get(assoc_obj_type_id, "")
                key = (assoc_module, obj_type_name, assoc_name)
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "module_name": assoc_module,
                        "object_type_name": obj_type_name,
                        "association_name": assoc_name,
                    })

            logger.info(f"get_associated_objects found {len(results)} associations for objectTypeId={object_type_id}")
            return results
        except Exception as e:
            logger.error(f"get_associated_objects failed for objectTypeId={object_type_id}: {e}")
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

    async def run_dynamic_query(
        self,
        module_name: str,
        object_type_name: str,
        field_names: Optional[List[str]] = None,
        filter_condition: str = "",
        max_records: int = 500,
        fetch_all: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch records via runDynamicQuery, optionally paginating through all results
        using the TRIRIGA continuationToken mechanism (runDynamicQueryContinue).

        Args:
            max_records: Max records for the initial page (default 500).
            fetch_all:   If True, follow continuation tokens until all records are fetched.
        """
        if self.demo_mode:
            from app.tririga_client.fixtures import get_demo_records
            return get_demo_records(module_name, object_type_name, max_records)

        loop = asyncio.get_event_loop()
        try:
            client = await loop.run_in_executor(None, self._get_zeep_client)

            ns_dto = "{http://dto.ws.tririga.com}"
            ns_ws = "{http://ws.tririga.com}"
            DisplayLabel = client.get_type(f"{ns_dto}DisplayLabel")
            ArrayOfDisplayLabel = client.get_type(f"{ns_dto}ArrayOfDisplayLabel")
            ContinuationToken = client.get_type(f"{ns_dto}ContinuationToken")
            empty_sort = client.get_type(f"{ns_dto}ArrayOfFieldSortOrder")()
            empty_filter = client.get_type(f"{ns_dto}ArrayOfFilter")()
            empty_assoc_filter = client.get_type(f"{ns_dto}ArrayOfAssociationFilter")()
            obj_names = client.get_type(f"{ns_ws}ArrayOfString")(string=[object_type_name])
            gui_names = client.get_type(f"{ns_ws}ArrayOfString")(string=[])

            display_labels = []
            for fname in (field_names or []):
                if "||" in fname:
                    section, clean = fname.split("||", 1)
                else:
                    section, clean = "", fname
                if clean:
                    display_labels.append(DisplayLabel(fieldName=clean, label=clean, sectionName=section))
            display_fields = ArrayOfDisplayLabel(DisplayLabel=display_labels) if display_labels else ArrayOfDisplayLabel()

            from app.tririga_client.normalizer import extract_dynamic_query_result

            # Initial query
            def _initial_call():
                return client.service.runDynamicQuery(
                    projectName="",
                    moduleName=module_name,
                    objectTypeNames=obj_names,
                    guiNames=gui_names,
                    associatedModuleName="",
                    associatedObjectTypeName="",
                    projectScope=2,
                    displayFields=display_fields,
                    associatedDisplayFields=ArrayOfDisplayLabel(),
                    fieldSortOrders=empty_sort,
                    filters=empty_filter,
                    associationFilters=empty_assoc_filter,
                    start=1,
                    maximumResultCount=max_records,
                )

            result = await loop.run_in_executor(None, _initial_call)
            records, token, total = extract_dynamic_query_result(result)

            logger.info(
                f"runDynamicQuery: got {len(records)} records, totalResults={total}, "
                f"token={'yes' if token else 'no'}"
            )

            # Follow continuation tokens if fetch_all is requested
            if fetch_all and token:
                while token:
                    token_str = token

                    def _continue_call(t=token_str):
                        return client.service.runDynamicQueryContinue(
                            continuationToken=ContinuationToken(tokenString=t)
                        )

                    try:
                        cont_result = await loop.run_in_executor(None, _continue_call)
                        page_records, token, _ = extract_dynamic_query_result(cont_result)
                    except Exception as cont_err:
                        logger.warning(
                            f"runDynamicQueryContinue failed after {len(records)} records: {cont_err}. "
                            f"Returning partial results."
                        )
                        break

                    if not page_records:
                        break

                    records.extend(page_records)
                    logger.info(
                        f"runDynamicQueryContinue: got {len(page_records)} more records "
                        f"(total so far: {len(records)}/{total})"
                    )

            return records

        except Exception as e:
            detail = getattr(e, "detail", None) or getattr(e, "message", None) or ""
            logger.error(f"runDynamicQuery failed for {module_name}/{object_type_name}: {e} | detail: {detail}")
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
