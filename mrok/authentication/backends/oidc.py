import logging

import httpx
import jwt

from mrok.authentication.base import AuthenticationError, AuthIdentity, BaseHTTPAuthBackend
from mrok.authentication.credentials import BearerCredentials
from mrok.authentication.registry import register_authentication_backend

logger = logging.getLogger("mrok.controller")
NOT_AUTHENTICATED = "UnAuthenticated."


@register_authentication_backend("oidc")
class OIDCJWTAuthenticationBackend(BaseHTTPAuthBackend):
    async def authenticate(self, authentication_header: str | None) -> AuthIdentity | None:
        async with httpx.AsyncClient() as client:
            try:
                credentials = BearerCredentials.from_authorization_header(authentication_header)
                if not credentials:
                    raise AuthenticationError("Invalid Bearer token")
                jwt_token = credentials.token
                config_resp = await client.get(self.config.config_url)
                config_resp.raise_for_status()
                config = config_resp.json()
                issuer = config["issuer"]
                jwks_uri = config["jwks_uri"]

                jwks_resp = await client.get(jwks_uri)
                jwks_resp.raise_for_status()
                jwks = jwks_resp.json()

                header = jwt.get_unverified_header(jwt_token)
                kid = header["kid"]

                key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)
            except Exception:
                logger.exception("Error fetching openid-config/jwks")
                raise AuthenticationError(NOT_AUTHENTICATED)
        if key_data is None:
            logger.error("Key ID not found in JWKS")

            raise AuthenticationError(NOT_AUTHENTICATED)
        try:
            payload = jwt.decode(
                jwt_token,
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
            logger.error(f"Invalid jwt token: {e} ({authentication_header})")
            raise AuthenticationError(NOT_AUTHENTICATED)
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid jwt token: {e} ({authentication_header})")
            raise AuthenticationError(NOT_AUTHENTICATED)
