from mrok.authentication.base import BaseHTTPAuthBackend

BACKEND_REGISTRY: dict[str, type[BaseHTTPAuthBackend]] = {}


def register_authentication_backend(name: str):
    """Decorator to register a backend class with a unique key."""

    def decorator(cls: type[BaseHTTPAuthBackend]):
        BACKEND_REGISTRY[name] = cls
        return cls

    return decorator


def get_authentication_backend(name: str) -> type[BaseHTTPAuthBackend] | None:
    return BACKEND_REGISTRY.get(name)
