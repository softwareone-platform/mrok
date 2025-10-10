import logging
from typing import Annotated

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mrok.controller.dependencies.conf import AppSettings

logger = logging.getLogger("mrok.controller")

UNAUTHORIZED_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized."
)


class JWTCredentials(HTTPAuthorizationCredentials):
    pass


class JWTBearer(HTTPBearer):
    def __init__(self):
        super().__init__(auto_error=False)

    async def __call__(self, request: Request) -> JWTCredentials:
        credentials = await super().__call__(request)
        if not credentials:
            raise UNAUTHORIZED_EXCEPTION
        try:
            return JWTCredentials(
                scheme=credentials.scheme,
                credentials=credentials.credentials,
            )
        except jwt.InvalidTokenError:
            raise UNAUTHORIZED_EXCEPTION


async def authenticate(
    settings: AppSettings,
    credentials: Annotated[JWTCredentials, Depends(JWTBearer())],
):
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=0.25,
            read=settings.auth.read_timeout,
            write=2.0,
            pool=5.0,
        ),
    ) as client:
        try:
            config_resp = await client.get(settings.auth.openid_config_url)
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
            audience=settings.auth.audience,
        )
        return payload
    except jwt.InvalidKeyError as e:
        logger.error(f"Invalid jwt token: {e} ({credentials.credentials})")
        raise UNAUTHORIZED_EXCEPTION
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid jwt token: {e} ({credentials.credentials})")
        raise UNAUTHORIZED_EXCEPTION
