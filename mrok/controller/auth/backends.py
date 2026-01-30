import logging

import httpx
import jwt
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.http import HTTPBase

from mrok.controller.auth.base import UNAUTHORIZED_EXCEPTION, AuthIdentity, BaseHTTPAuthBackend
from mrok.controller.auth.registry import register_authentication_backend

logger = logging.getLogger("mrok.controller")


@register_authentication_backend("oidc")
class OIDCJWTAuthenticationBackend(BaseHTTPAuthBackend):
    def init_scheme(self) -> HTTPBase:
        return HTTPBearer(auto_error=False)

    async def authenticate(self, credentials: HTTPAuthorizationCredentials) -> AuthIdentity | None:
        async with httpx.AsyncClient() as client:
            try:
                config_resp = await client.get(self.config.config_url)
                config_resp.raise_for_status()
                config = config_resp.json()
                issuer = config["issuer"]
                jwks_uri = config["jwks_uri"]

                jwks_resp = await client.get(jwks_uri)
                jwks_resp.raise_for_status()
                jwks = jwks_resp.json()

                header = jwt.get_unverified_header(credentials.credentials)
                kid = header["kid"]

                key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)
            except Exception:
                logger.exception("Error fetching openid-config/jwks")
                raise UNAUTHORIZED_EXCEPTION
        if key_data is None:
            logger.error("Key ID not found in JWKS")
            raise UNAUTHORIZED_EXCEPTION

        try:
            payload = jwt.decode(
                credentials.credentials,
                jwt.PyJWK(key_data),
                algorithms=[header["alg"]],
                issuer=issuer,
                audience=self.config.audience,
            )
            return AuthIdentity(
                subject=payload["sub"],
                metadata=payload,
            )
        except jwt.InvalidKeyError as e:
            logger.error(f"Invalid jwt token: {e} ({credentials.credentials})")
            raise UNAUTHORIZED_EXCEPTION
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid jwt token: {e} ({credentials.credentials})")
            raise UNAUTHORIZED_EXCEPTION
