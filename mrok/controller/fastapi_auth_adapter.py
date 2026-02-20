from fastapi import HTTPException, Request
from starlette import status

from mrok.authentication.base import AuthenticationError
from mrok.authentication.manager import HTTPAuthManager


def build_fastapi_auth_dependencies(auth_manager: HTTPAuthManager):
    async def auth_dependency(request: Request):
        try:
            return await auth_manager.authenticate(request.headers.get("authorization"))
        except AuthenticationError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )

    return auth_dependency
