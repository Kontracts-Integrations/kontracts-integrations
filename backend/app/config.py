from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application
    app_name: str = "TRIRIGA-Kontracts Integration"
    debug: bool = False
    log_level: str = "INFO"
    demo_mode: bool = False

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/tririga_kontracts"
    )

    # Security
    fernet_key: Optional[str] = None
    # Restrict API access to members of this GitHub org (leave unset to allow any valid GitHub user)
    github_org: Optional[str] = None

    # CORS — defaults to * for local dev; set CORS_ORIGINS=https://... in production
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # TRIRIGA
    tririga_url: str = "https://your-instance.tririga.com"
    tririga_username: Optional[str] = None
    tririga_password: Optional[str] = None
    tririga_wsdl_path: str = "/ws/TririgaWS?wsdl"

    # Kontracts
    kontracts_base_url: str = "https://api-dev.kontracts.pro"
    kontracts_auth0_domain: Optional[str] = None
    kontracts_client_id: Optional[str] = None
    kontracts_client_secret: Optional[str] = None
    kontracts_audience: Optional[str] = None

    # Fixtures path (relative to app root)
    fixtures_path: str = "fixtures"


settings = Settings()
