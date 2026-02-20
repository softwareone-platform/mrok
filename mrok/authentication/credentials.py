from abc import ABC, abstractmethod
from dataclasses import dataclass


class Credentials(ABC):
    @classmethod
    @abstractmethod
    def from_authorization_header(cls, authorization_header: str | None):
        pass  # pragma: no cover


@dataclass
class BearerCredentials(Credentials):
    token: str

    @classmethod
    def from_authorization_header(cls, authorization_header: str | None):
        """
        Extract bearer token from authorization header
        :param authorization_header: the authorization 'Bearer xyz' string
        :return: the token string or None
        """
        if not authorization_header:
            return None
        schema, _, value = authorization_header.partition(" ")
        if schema.lower() != "bearer" or not value:
            return None
        return cls(token=value.strip())
