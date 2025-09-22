from collections.abc import Callable

import pytest
from dynaconf import Dynaconf

from mrok.conf import Settings

SettingsFactory = Callable[..., Settings]


@pytest.fixture
def settings_factory() -> SettingsFactory:
    def _get_settings(ziti: dict | None = None) -> Settings:
        ziti = ziti or {
            "url": "https://ziti.example.com",
            "read_timeout": 10,
            "ssl_verify": True,
            "auth": {"username": "user", "password": "pass", "identity": None},
        }
        settings = Dynaconf(
            environments=True, settings_files=[], ENV_FOR_DYNACONF="testing", ZITI=ziti
        )
        return settings

    return _get_settings
