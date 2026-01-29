from dynaconf import Dynaconf, LazySettings

type Settings = LazySettings

DEFAULT_SETTINGS = {
    "LOGGING": {
        "debug": False,
        "rich": False,
    },
    "FRONTEND": {
        "identity": "public",
        "mode": "zrok",
    },
    "ZITI": {
        "ssl_verify": False,
    },
    "CONTROLLER": {
        "pagination": {"limit": 50},
    },
    "IDENTIFIERS": {
        "extension": {
            "regex": "(?i)EXT-\\d{4}-\\d{4}",
            "format": "EXT-xxxx-yyyy",
            "example": "EXT-2000-1000",
        },
        "instance": {
            "regex": "(?i)INS-\\d{4}-\\d{4}-\\d{4}",
            "format": "INS-xxxx-yyyy-zzzz",
            "example": "INS-2004-2000-3000",
        },
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
