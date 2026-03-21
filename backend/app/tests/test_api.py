"""
API endpoint integration tests using httpx AsyncClient.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestConnectionsAPI:
    @pytest.mark.asyncio
    async def test_list_connections_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/connections/")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_tririga_connection(self, client: AsyncClient):
        payload = {
            "name": "Test TRIRIGA",
            "connection_type": "tririga",
            "base_url": "https://test.tririga.com",
            "credentials": {
                "username": "admin",
                "password": "secret",
                "wsdl_path": "/ws/TririgaWS?wsdl",
            },
        }
        resp = await client.post("/api/v1/connections/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test TRIRIGA"
        assert data["connection_type"] == "tririga"
        assert "id" in data
        # Credentials should NOT be returned in response
        assert "credentials" not in data
        assert "encrypted_credentials" not in data

    @pytest.mark.asyncio
    async def test_create_kontracts_connection(self, client: AsyncClient):
        payload = {
            "name": "Test Kontracts",
            "connection_type": "kontracts",
            "base_url": "https://api-dev.kontracts.pro",
            "credentials": {
                "auth0_domain": "test.auth0.com",
                "client_id": "cid",
                "client_secret": "csecret",
                "audience": "https://api.kontracts.pro",
            },
        }
        resp = await client.post("/api/v1/connections/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["connection_type"] == "kontracts"

    @pytest.mark.asyncio
    async def test_get_connection_by_id(self, client: AsyncClient):
        # Create first
        create_resp = await client.post(
            "/api/v1/connections/",
            json={
                "name": "For Get Test",
                "connection_type": "tririga",
                "base_url": "https://x.com",
                "credentials": {"username": "u", "password": "p"},
            },
        )
        conn_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/connections/{conn_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == conn_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_connection_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/connections/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_connection(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/v1/connections/",
            json={
                "name": "Update Test",
                "connection_type": "tririga",
                "base_url": "https://x.com",
                "credentials": {"username": "u", "password": "p"},
            },
        )
        conn_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/connections/{conn_id}",
            json={"name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_connection(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/v1/connections/",
            json={
                "name": "Delete Test",
                "connection_type": "tririga",
                "base_url": "https://x.com",
                "credentials": {"username": "u", "password": "p"},
            },
        )
        conn_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/connections/{conn_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/v1/connections/{conn_id}")
        assert resp.status_code == 404


class TestMappingsAPI:
    @pytest.mark.asyncio
    async def test_list_mappings_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/mappings/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_mapping(self, client: AsyncClient):
        payload = {
            "name": "Lease Sync Mapping",
            "description": "Maps TRIRIGA leases to Kontracts",
            "tririga_module": "triRealEstateLease",
            "tririga_query_name": "All Active Leases",
            "kontracts_endpoint": "/api/v1/leases/",
            "kontracts_method": "POST",
            "field_mappings": [
                {
                    "id": "fm1",
                    "source_field": "triNameTX",
                    "target_field": "name",
                    "transform_type": "direct",
                    "is_required": True,
                },
                {
                    "id": "fm2",
                    "source_field": "triLeaseTypeCL",
                    "target_field": "lease_type",
                    "transform_type": "lookup_table",
                    "transform_config": {
                        "table": {"Operating": "operating", "Finance": "finance"}
                    },
                },
            ],
        }
        resp = await client.post("/api/v1/mappings/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Lease Sync Mapping"
        assert data["tririga_module"] == "triRealEstateLease"
        assert data["current_version"] is not None
        assert data["current_version"]["version_number"] == 1

    @pytest.mark.asyncio
    async def test_update_mapping_creates_new_version(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/v1/mappings/",
            json={
                "name": "Version Test",
                "field_mappings": [
                    {
                        "id": "v1",
                        "source_field": "triNameTX",
                        "target_field": "name",
                        "transform_type": "direct",
                    }
                ],
            },
        )
        mapping_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/v1/mappings/{mapping_id}",
            json={
                "field_mappings": [
                    {
                        "id": "v2",
                        "source_field": "triNameTX",
                        "target_field": "name",
                        "transform_type": "direct",
                    },
                    {
                        "id": "v2b",
                        "source_field": "triLeaseTypeCL",
                        "target_field": "lease_type",
                        "transform_type": "direct",
                    },
                ]
            },
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["current_version"]["version_number"] == 2

    @pytest.mark.asyncio
    async def test_delete_mapping(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/v1/mappings/",
            json={"name": "To Delete", "field_mappings": []},
        )
        mapping_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/mappings/{mapping_id}")
        assert resp.status_code == 204


class TestRunsAPI:
    @pytest.mark.asyncio
    async def test_list_runs_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/runs/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_trigger_run_requires_valid_mapping(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/runs/",
            json={"mapping_template_id": 99999},
        )
        assert resp.status_code == 404


class TestLogsAPI:
    @pytest.mark.asyncio
    async def test_list_logs_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/logs/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_log_stats(self, client: AsyncClient):
        resp = await client.get("/api/v1/logs/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert "info" in data["stats"]
        assert "error" in data["stats"]
