# TRIRIGA ↔ Kontracts Integration Platform

A production-quality full-stack integration application that bridges IBM TRIRIGA (via SOAP API) with the Kontracts lease accounting platform (REST API). Provides a visual mapping builder, configurable field transforms, scheduled sync runs, and comprehensive audit logging.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (3000)                   │
│  Dashboard | Connections | Mappings | Runs | Logs            │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (REST)
┌──────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend (8000)                       │
│  /api/v1/connections  /api/v1/mappings  /api/v1/runs         │
│  /api/v1/tririga      /api/v1/kontracts /api/v1/logs         │
└──────┬────────────────────────────────────────┬─────────────┘
       │ SOAP (zeep)                             │ HTTP (httpx)
┌──────▼───────────┐                  ┌──────────▼────────────┐
│  IBM TRIRIGA     │                  │   Kontracts API       │
│  your-instance.  │                  │   api-dev.kontracts   │
│  tririga.com     │                  │   .pro                │
└──────────────────┘                  └───────────────────────┘
       │
┌──────▼───────────┐
│  PostgreSQL 15   │
│  (persistent     │
│   storage)       │
└──────────────────┘
```

---

## Prerequisites

- Docker Desktop 4.x+ with Docker Compose v2
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)
- Git

---

## Quick Start (Docker)

### 1. Clone and configure

```bash
git clone <repo-url>
cd tririga-kontracts-integration
cp .env.example .env
```

### 2. Edit `.env` with your credentials

```bash
# Minimum required:
TRIRIGA_URL=https://your-instance.tririga.com
TRIRIGA_USERNAME=your_username
TRIRIGA_PASSWORD=your_password

KONTRACTS_BASE_URL=https://api-dev.kontracts.pro
KONTRACTS_AUTH0_DOMAIN=your-tenant.auth0.com
KONTRACTS_CLIENT_ID=your_client_id
KONTRACTS_CLIENT_SECRET=your_client_secret
KONTRACTS_AUDIENCE=https://api-dev.kontracts.pro
```

### 3. Start all services

```bash
docker-compose up --build
```

Services start at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

### 4. Run database migrations

```bash
docker-compose exec backend alembic upgrade head
```

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tririga_kontracts
export FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export DEMO_MODE=true  # Uses fixture data instead of live TRIRIGA

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # or set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## Demo Mode

Set `DEMO_MODE=true` in your `.env` to use fixture data instead of connecting to live TRIRIGA. This allows UI exploration without credentials.

Fixture files are in `fixtures/`:
- `sample_tririga_response.json` - Mock SOAP response
- `sample_mapping_template.json` - Pre-built mapping config
- `sample_kontracts_payload.json` - Expected transformed output

---

## Running Tests

```bash
# Backend tests
cd backend
pytest app/tests/ -v --asyncio-mode=auto

# Frontend type checking
cd frontend
npm run type-check
```

---

## Feature Overview

### Connections
Configure and test TRIRIGA SOAP credentials and Kontracts Auth0 credentials. Credentials are encrypted at rest using Fernet symmetric encryption.

### Mappings
Visual drag-and-drop field mapper:
- **Left panel**: TRIRIGA fields from any module/query
- **Right panel**: Kontracts endpoint fields from OpenAPI schema
- **Center**: Mapping rows with configurable transforms

Supported transforms:
| Transform | Description |
|-----------|-------------|
| `direct` | Copy value as-is |
| `constant` | Always use a fixed value |
| `date_format` | Convert date string formats |
| `number_convert` | Parse/round numbers |
| `boolean_convert` | Convert truthy strings to bool |
| `string_template` | Jinja2-style `{field}` templates |
| `lookup_table` | Map discrete values to other values |
| `json_path` | Extract via JSONPath from nested data |

### Sync Runs
Trigger manual or scheduled syncs. Each run:
1. Fetches records from TRIRIGA using the configured query
2. Applies field mappings and transforms
3. Validates against Kontracts schema
4. POSTs/PUTs to Kontracts API
5. Logs per-record success/failure

### Logs
Full audit trail with search and filtering by level (debug/info/warning/error), run, and timestamp.

---

## API Reference

Full interactive docs at http://localhost:8000/docs (Swagger UI) and http://localhost:8000/redoc.

Key endpoints:

```
GET  /api/v1/connections/          List all connections
POST /api/v1/connections/          Create connection
POST /api/v1/connections/{id}/test Test connection

GET  /api/v1/tririga/modules       List TRIRIGA modules
POST /api/v1/tririga/query         Run TRIRIGA query
POST /api/v1/tririga/preview       Preview data

GET  /api/v1/kontracts/endpoints   List Kontracts endpoints
GET  /api/v1/kontracts/schema      Get endpoint schema

GET  /api/v1/mappings/             List mapping templates
POST /api/v1/mappings/             Create mapping
PUT  /api/v1/mappings/{id}         Update mapping

POST /api/v1/runs/                 Trigger sync run
GET  /api/v1/runs/                 List runs
GET  /api/v1/runs/{id}             Run detail with records

GET  /api/v1/logs/                 Query logs
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `FERNET_KEY` | Yes | — | Encryption key (generate with `Fernet.generate_key()`) |
| `DEMO_MODE` | No | `false` | Use fixture data instead of live APIs |
| `TRIRIGA_URL` | No | — | TRIRIGA base URL |
| `TRIRIGA_USERNAME` | No | — | TRIRIGA username |
| `TRIRIGA_PASSWORD` | No | — | TRIRIGA password |
| `KONTRACTS_BASE_URL` | No | `https://api-dev.kontracts.pro` | Kontracts API base |
| `KONTRACTS_AUTH0_DOMAIN` | No | — | Auth0 domain for Kontracts |
| `KONTRACTS_CLIENT_ID` | No | — | Auth0 client ID |
| `KONTRACTS_CLIENT_SECRET` | No | — | Auth0 client secret |
| `KONTRACTS_AUDIENCE` | No | — | Auth0 audience |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Allowed CORS origins |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend URL for frontend |

---

## Project Structure

```
tririga-kontracts-integration/
├── README.md
├── .env.example
├── docker-compose.yml
├── fixtures/
│   ├── sample_tririga_response.json
│   ├── sample_mapping_template.json
│   └── sample_kontracts_payload.json
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/001_initial.py
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       ├── schemas/
│       ├── api/
│       ├── tririga_client/
│       ├── kontracts_client/
│       ├── mapping_engine/
│       ├── sync_service/
│       └── tests/
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── next.config.ts
    ├── Dockerfile
    └── src/
        ├── app/
        ├── components/
        ├── lib/
        └── types/
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## License

MIT License - see LICENSE file for details.
