from dynaconf import Dynaconf, LazySettings

type Settings = LazySettings

DEFAULT_SETTINGS = {
    "logging__debug": False,
    "logging__rich": False,
    "proxy__identity": "public",
    "proxy__mode": "zrok",  # change for mrok
    "ziti__ssl_verify": True,
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
