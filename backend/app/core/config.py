"""
Core Configuration - Production Forcing Framework Compliant
Handles environment variables and GCP Secret Manager integration
"""
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from google.cloud import secretmanager


class Settings(BaseSettings):
    """
    Application settings with automatic Secret Manager integration.

    PFF Security Gates:
    - ✅ No hardcoded secrets
    - ✅ All secrets from Secret Manager in production
    - ✅ Environment variables for local development
    - ✅ Type validation on all config
    """

    # Application
    APP_NAME: str = "MemCloud API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production")  # production, staging, development

    # GCP Configuration
    GCP_PROJECT_ID: str = Field(default="memmachine-cloud")
    GCP_REGION: str = Field(default="us-central1")

    # Database Configuration
    DB_HOST: str = Field(default="/cloudsql/memmachine-cloud:us-central1:memmachine-db")
    DB_NAME: str = Field(default="memmachine")
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: Optional[str] = Field(default=None)  # Will be loaded from Secret Manager

    # Cloud SQL Connection
    CLOUD_SQL_CONNECTION_NAME: str = Field(
        default="memmachine-cloud:us-central1:memmachine-db"
    )
    USE_CLOUD_SQL_CONNECTOR: bool = Field(default=True)

    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = Field(default="memmachine-cloud")
    FIREBASE_CREDENTIALS_PATH: Optional[str] = Field(default=None)

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8000",
            "https://memcloud-frontend-576223366889.us-central1.run.app",
            "https://memcloud-api-576223366889.us-central1.run.app",
            "*",  # Allow all origins for hackathon demo
        ]
    )

    # Security
    SECRET_KEY: Optional[str] = Field(default=None)  # Will be loaded from Secret Manager
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Cloud Run Configuration
    PORT: int = Field(default=8080)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    @field_validator("DEBUG", mode="after")
    @classmethod
    def validate_debug(cls, v: bool, info) -> bool:
        """Ensure DEBUG is False in production"""
        # Only validate if ENVIRONMENT is explicitly set
        env = info.data.get("ENVIRONMENT")
        if env == "production" and v is True:
            raise ValueError("DEBUG must be False in production environment")
        return v

    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        """
        Retrieve secret from GCP Secret Manager.

        PFF Security Gate: All secrets MUST come from Secret Manager in production

        Args:
            secret_name: Name of the secret in Secret Manager
            version: Version of the secret (default: latest)

        Returns:
            Secret value as string

        Raises:
            Exception: If secret cannot be retrieved in production
        """
        # In development, allow fallback to environment variables
        if self.ENVIRONMENT == "development":
            env_value = os.getenv(secret_name.upper())
            if env_value:
                return env_value

        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.GCP_PROJECT_ID}/secrets/{secret_name}/versions/{version}"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            if self.ENVIRONMENT == "production":
                raise Exception(
                    f"Failed to retrieve secret '{secret_name}' from Secret Manager. "
                    f"Production requires Secret Manager. Error: {e}"
                )
            # In development, provide helpful error
            raise Exception(
                f"Secret '{secret_name}' not found. "
                f"Set environment variable or add to Secret Manager. Error: {e}"
            )

    def load_secrets(self) -> None:
        """
        Load all required secrets from Secret Manager.
        Called during application startup.

        PFF Security Gate: Fail fast if secrets are missing
        """
        # Database password
        if not self.DB_PASSWORD:
            self.DB_PASSWORD = self.get_secret("database-password")

        # Secret key for JWT
        if not self.SECRET_KEY:
            self.SECRET_KEY = self.get_secret("api-secret-key")

    def get_database_url(self) -> str:
        """
        Get database connection URL.

        Returns:
            SQLAlchemy-compatible database URL
        """
        if self.USE_CLOUD_SQL_CONNECTOR:
            # Cloud SQL Connector will handle the connection
            return (
                f"postgresql+pg8000://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@/{self.DB_NAME}?unix_sock=/cloudsql/{self.CLOUD_SQL_CONNECTION_NAME}/.s.PGSQL.5432"
            )
        else:
            # Direct connection (local development with Cloud SQL Proxy)
            return (
                f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}/{self.DB_NAME}"
            )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to ensure we only load secrets once.

    Returns:
        Settings instance with secrets loaded
    """
    settings = Settings()

    # Load secrets from Secret Manager (only in production/staging)
    if settings.ENVIRONMENT in ["production", "staging"]:
        settings.load_secrets()

    return settings


# Export settings instance
settings = get_settings()
