from mrok.errors import MrokError


class ProxyIdentityNotFoundError(MrokError):
    pass


class ProxyIdentityAlreadyExistsError(MrokError):
    pass


class ServiceNotFoundError(MrokError):
    pass


class UserIdentityNotFoundError(MrokError):
    pass


class ConfigTypeNotFoundError(MrokError):
    pass


class ServiceAlreadyRegisteredError(MrokError):
    pass
