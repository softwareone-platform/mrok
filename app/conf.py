import pathlib
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


class Settings(BaseSettings):
    """
    This class store the Operations API settings.
    """
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="MROK_",
        extra="ignore",
    )

    ziti_api_endpoint: str
    ziti_auth_type: str = "password"
    ziti_username: str | None = None
    ziti_password: str | None = None
    ziti_identity: str | None = None
    api_client_read_timeout_seconds: float = 30




_settings = None


def get_settings() -> Settings:
    global _settings
    if not _settings:
        _settings = Settings()
    return _settings
