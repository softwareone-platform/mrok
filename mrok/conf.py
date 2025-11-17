from dynaconf import Dynaconf, LazySettings

type Settings = LazySettings

DEFAULT_SETTINGS = {
    "LOGGING": {
        "debug": False,
        "rich": False,
    },
    "PROXY": {
        "identity": "public",
        "mode": "zrok",
    },
    "ZITI": {
        "ssl_verify": False,
    },
    "PAGINATION": {"limit": 50},
    "SIDECAR": {
        "textual_port": 4040,
        "store_port": 5051,
        "store_size": 1000,
        "textual_command": "python mrok/agent/sidecar/inspector.py",
    },
}

_settings = None


def get_settings() -> Settings:
    global _settings
    if not _settings:
        _settings = Dynaconf(
            envvar_prefix="MROK",
            settings_files=["settings.yaml", ".secrets.yaml"],
            merge_enabled=True,
        )
        _settings.configure(**DEFAULT_SETTINGS)
    return _settings
