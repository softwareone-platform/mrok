import logging

import httpx
import jwt

from mrok.authentication.base import AuthIdentity, BaseHTTPAuthBackend
from mrok.authentication.credentials import BearerCredentials, Credentials
from mrok.authentication.registry import register_authentication_backend
from mrok.types.proxy import Scope

logger = logging.getLogger("mrok.authentication")


@register_authentication_backend("oidc")
class OIDCJWTAuthenticationBackend(BaseHTTPAuthBackend):
    def get_credentials(self, scope: Scope) -> Credentials | None:
        return BearerCredentials.extract_from_asgi_scope(scope)

    async def authenticate(self, credentials: Credentials) -> AuthIdentity | None:
        async with httpx.AsyncClient() as client:
            try:
                jwt_token = credentials.credentials
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
                return None
        if key_data is None:
            logger.error("Key ID not found in JWKS")
            return None
        try:
            payload = jwt.decode(
                jwt_token,
                jwt.PyJWK(key_data),
                algorithms=[header["alg"]],
                issuer=issuer,
                audience=self.config.audience,
            )
            return AuthIdentity(
                subject=payload.get(self.config.subject_claim) or "",
                metadata=payload,
            )
        except jwt.InvalidKeyError as e:
            logger.error(f"Invalid jwt token: {e}")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid jwt token: {e}")
            return None
