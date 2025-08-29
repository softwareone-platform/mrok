import json
import os
import ssl
import tempfile
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.clients.base import APIClientError, BaseAPIClient, BaseApiClientAuth


class ZitiClientError(APIClientError):
    pass


class ZitiAuthError(APIClientError):
    pass


class ZitiIdentityAuthContext:
    def __init__(self, identity_path: str):
        identity = json.load(open(identity_path))
        cert_data = identity["id"]["cert"][4:]
        key_data = identity["id"]["key"][4:]
        ca_data = identity["id"]["ca"][4:]
        self.key_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem")
        self.cert_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem")
        self.ca_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem")
        self.cert_file.write(cert_data)
        self.key_file.write(key_data)
        self.ca_file.write(ca_data)
        self.cert_file.close()
        self.key_file.close()
        self.ca_file.close()
        self.ssl_context = ssl.create_default_context(
            cafile=self.ca_file.name,
        )
        self.ssl_context.load_cert_chain(certfile=self.cert_file.name, keyfile=self.key_file.name)
        self.destroy()

    def destroy(self):
        os.unlink(self.cert_file.name)
        os.unlink(self.key_file.name)
        os.unlink(self.ca_file.name)


class ZitiPasswordAuth(BaseApiClientAuth):
    requires_response_body = True

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        request.headers["zt-session"] = self.client.token
        response = yield request

        if response.status_code == 401:
            refresh_request = self.build_refresh_request()
            refresh_response = yield refresh_request
            await refresh_response.aread()
            self.update_token(refresh_response)
            request.headers["zt-session"] = self.client.token
            yield request

    def build_refresh_request(self) -> httpx.Request:
        """Builds the token refresh request."""
        return httpx.Request(
            "POST",
            f"{self.client.base_url}/authenticate",
            params={"method": "password"},
            json={
                "username": self.client.settings.ziti_username,
                "password": self.client.settings.ziti_password,
            },
        )


class ZitiIdentityAuth(BaseApiClientAuth):
    requires_response_body = True

    def __init__(self, client: BaseAPIClient):
        super().__init__(client)
        self.identity_context = ZitiIdentityAuthContext(self.client.settings.ziti_identity)

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        request.headers["zt-session"] = self.client.token
        response = yield request

        if response.status_code == 401:
            # Use the new client certificate authentication method
            refresh_response = await self.get_auth_token()
            # await refresh_response.aread()
            self.update_token(refresh_response)
            request.headers["zt-session"] = self.client.token
            yield request

    async def get_auth_token(self):
        async with httpx.AsyncClient(
            base_url=self.client.base_url,
            verify=self.identity_context.ssl_context,
        ) as client:
            response = await client.post(
                "/authenticate",
                params={"method": "cert"},
            )
            return response


class ZitiClient(BaseAPIClient):
    @property
    def base_url(self):
        return self.settings.ziti_api_endpoint

    @property
    def auth(self):
        if self.settings.ziti_auth_type == "password":
            return ZitiPasswordAuth(self)
        elif self.settings.ziti_auth_type == "identity":
            return ZitiIdentityAuth(self)
        else:
            raise ZitiAuthError("Unsupported authentication method")

    def services(self) -> AsyncGenerator[dict[str, Any], None]:
        return self.collection_iterator("/services")

    def identities(self) -> AsyncGenerator[dict[str, Any], None]:
        return self.collection_iterator("/identities")
