from fastapi import HTTPException, Request, status

from mrok.authentication.manager import HTTPAuthManager


def build_fastapi_auth_dependencies(auth_manager: HTTPAuthManager):
    async def auth_dependency(request: Request):
        identity = await auth_manager(request.scope)
        if identity is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )
        return identity

    return auth_dependency
