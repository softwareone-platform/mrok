import logging

import jwt
from jwt import InvalidKeyError, InvalidTokenError

from mrok.authentication.base import AuthIdentity, BaseHTTPAuthBackend
from mrok.authentication.credentials import BearerCredentials, Credentials
from mrok.authentication.registry import register_authentication_backend
from mrok.types.proxy import Scope

logger = logging.getLogger("mrok.authentication")


@register_authentication_backend("jwt")
class JWTAuthenticationBackend(BaseHTTPAuthBackend):
    def get_credentials(self, scope: Scope) -> Credentials | None:
        return BearerCredentials.extract_from_asgi_scope(scope)

    async def authenticate(self, credentials: Credentials) -> AuthIdentity | None:
        try:
            jwt_token = credentials.credentials
            claims = jwt.decode(
                jwt_token,
                key=self.config.secret,
                audience=self.config.audience,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": False,
                },
            )
            return AuthIdentity(subject=claims["sub"], metadata=claims)
        except InvalidTokenError as error:
            logger.exception(f"Error decoding token {error}")
            return None
        except InvalidKeyError as error:
            logger.exception(f"Error decoding token {error}")
            return None
