import json
import logging
import ssl
import tempfile
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from functools import cached_property
from types import TracebackType
from typing import Any, Literal

import httpx

from mrok.conf import Settings
from mrok.types.ziti import Tags
from mrok.ziti.constants import MROK_VERSION_TAG, MROK_VERSION_TAG_NAME

logger = logging.getLogger(__name__)


class ZitiAPIError(Exception):
    pass


class ZitiAuthError(ZitiAPIError):
    pass


class ZitiBadRequestError(ZitiAPIError):
    def __init__(self, response: dict[str, Any]):
        self.response = response

    def __str__(self) -> str:
        err = self.response["error"]
        cause = err["cause"]
        return f"{err['code']} - {err['message']} ({cause['field']}: {cause['reason']})"


class BaseZitiAPI(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.limit = self.settings.pagination.limit
        self.token = None

    @property
    @abstractmethod
    def base_url(self):
        raise NotImplementedError("base_url property must be implemented in subclasses")

    @property
    def auth(self):
        if self.settings.ziti.auth.get("username") and self.settings.ziti.auth.get("password"):
            return ZitiPasswordAuth(self)
        elif self.settings.ziti.auth.get("identity"):
            return ZitiIdentityAuth(self)
        else:
            raise ZitiAuthError("Unsupported authentication method for OpenZiti.")

    @cached_property
    def httpx_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            auth=self.auth,
            verify=self.settings.ziti.ssl_verify,
            timeout=httpx.Timeout(
                connect=0.25,
                read=self.settings.ziti.read_timeout,
                write=2.0,
                pool=5.0,
            ),
        )

    async def create(self, endpoint: str, payload: dict[str, Any], tags: Tags | None) -> str:
        payload["tags"] = self._merge_tags(tags)
        response: httpx.Response = await self.httpx_client.post(
            endpoint,
            json=payload,
        )
        if response.status_code == 400:
            raise ZitiBadRequestError(response.json())
        response.raise_for_status()
        return response.json()["data"]["id"]

    async def get(
        self,
        endpoint: str,
        id: str,
        additional_path: str | None = None,
    ) -> dict[str, Any]:
        url = f"{endpoint}/{id}"
        if additional_path:
            url = f"{url}/{additional_path}"
        response = await self.httpx_client.get(url)
        response.raise_for_status()
        return response.json()["data"]

    async def delete(self, endpoint: str, id: str) -> None:
        response = await self.httpx_client.delete(f"{endpoint}/{id}")
        response.raise_for_status()
        return response.json()

    async def search_by_id_or_name(self, endpoint: str, id_or_name: str) -> dict[str, Any] | None:
        query = (
            f'(id="{id_or_name}" or name="{id_or_name.lower()}") '
            f"and tags.{MROK_VERSION_TAG_NAME} != null"
        )
        response = await self.httpx_client.get(
            endpoint,
            params={"filter": query},
        )
        if response.status_code == 400:
            raise ZitiBadRequestError(response.json())
        response.raise_for_status()
        response_data = response.json()
        if response_data["meta"]["pagination"]["totalCount"] == 1:
            return response_data["data"][0]

    async def get_page(
        self, endpoint: str, limit: int, offset: int, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        params = params or {}
        params["limit"] = limit
        params["offset"] = offset
        page_response = await self.httpx_client.get(endpoint, params=params)
        page_response.raise_for_status()
        page = page_response.json()
        return page

    async def collection_iterator(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> AsyncGenerator[dict, None]:
        offset = 0
        while True:
            page = await self.get_page(endpoint, self.limit, offset, params=params)
            items = page["data"]

            for item in items:
                yield item

            pagination_meta = page["meta"]["pagination"]
            total = pagination_meta["totalCount"]
            if total <= self.limit + offset:
                break

            offset = offset + self.limit

    async def __aenter__(self):
        await self.httpx_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> None:
        return await self.httpx_client.__aexit__(exc_type, exc_val, exc_tb)

    def _merge_tags(self, tags: Tags | None) -> Tags:
        prepared_tags: Tags = tags or {}
        prepared_tags.update(MROK_VERSION_TAG)
        return prepared_tags


class BaseZitiAuth(httpx.Auth):
    def __init__(self, api: BaseZitiAPI):
        self.api = api

    def update_token(self, response: httpx.Response) -> None:
        response.raise_for_status()
        data = response.json()
        self.api.token = data["data"]["token"]


class ZitiIdentityAuthContext:
    def __init__(self, identity_path: str):
        identity = json.load(open(identity_path))
        cert_data = identity["id"]["cert"][4:]
        key_data = identity["id"]["key"][4:]
        ca_data = identity["id"]["ca"][4:]
        with (
            tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as key_file,
            tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as cert_file,
            tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as ca_file,
        ):
            key_file.write(key_data)
            key_file.flush()
            cert_file.write(cert_data)
            cert_file.flush()
            ca_file.write(ca_data)
            ca_file.flush()
            self.ssl_context = ssl.create_default_context(
                cafile=ca_file.name,
            )
            self.ssl_context.load_cert_chain(
                keyfile=key_file.name,
                certfile=cert_file.name,
            )


class ZitiPasswordAuth(BaseZitiAuth):
    requires_response_body = True

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        request.headers["zt-session"] = self.api.token or ""
        response = yield request

        if response.status_code == 401:  # pragma: no branch
            refresh_request = self.build_refresh_request()
            refresh_response = yield refresh_request
            await refresh_response.aread()
            self.update_token(refresh_response)
            request.headers["zt-session"] = self.api.token or ""
            yield request

    def build_refresh_request(self) -> httpx.Request:
        """Builds the token refresh request."""
        return httpx.Request(
            "POST",
            f"{self.api.base_url}/authenticate",
            params={"method": "password"},
            json={
                "username": self.api.settings.ziti.auth.username,
                "password": self.api.settings.ziti.auth.password,
            },
        )


class ZitiIdentityAuth(BaseZitiAuth):
    requires_response_body = True

    def __init__(self, client: BaseZitiAPI):
        super().__init__(client)
        self.identity_context = ZitiIdentityAuthContext(self.api.settings.ziti.auth.identity)

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        request.headers["zt-session"] = self.api.token or ""
        response = yield request

        if response.status_code == 401:  # pragma: no cover
            # Use the new client certificate authentication method
            refresh_response = await self.get_auth_token()
            # await refresh_response.aread()
            self.update_token(refresh_response)
            request.headers["zt-session"] = self.api.token or ""
            yield request

    async def get_auth_token(self):
        async with httpx.AsyncClient(
            base_url=self.api.base_url,
            verify=self.identity_context.ssl_context,
        ) as client:
            response = await client.post(
                "/authenticate",
                params={"method": "cert"},
            )
            return response


class ZitiManagementAPI(BaseZitiAPI):
    @property
    def base_url(self):
        return f"{self.settings.ziti.api.management}/edge/management/v1"

    def services(
        self,
        params: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        return self.collection_iterator("/services", params=params)

    def identities(
        self,
        params: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        return self.collection_iterator("/identities", params=params)

    async def search_config(self, id_or_name) -> dict[str, Any] | None:
        return await self.search_by_id_or_name("/configs", id_or_name)

    async def create_config(self, name: str, config_type_id: str, tags: Tags | None = None) -> str:
        return await self.create(
            "/configs",
            {
                "configTypeId": config_type_id,
                "name": name,
                "data": {
                    "auth_scheme": "none",
                    "basic_auth": None,
                    "interstitial": True,
                    "oauth": None,
                },
            },
            tags,
        )

    async def delete_config(self, config_id: str) -> None:
        return await self.delete("/configs", config_id)

    async def create_config_type(self, name: str, tags: Tags | None = None) -> str:
        return await self.create(
            "/config-types",
            {
                "name": name,
                "schema": {},
            },
            tags,
        )

    async def create_service(
        self,
        name: str,
        config_id: str,
        tags: Tags | None = None,
    ) -> str:
        return await self.create(
            "/services",
            {
                "name": name,
                "configs": [config_id],
                "encryptionRequired": True,
            },
            tags,
        )

    async def create_service_router_policy(
        self,
        name: str,
        service_id: str,
        tags: Tags | None = None,
    ) -> str:
        return await self.create(
            "/service-edge-router-policies",
            {
                "name": name,
                "edgeRouterRoles": ["#all"],
                "serviceRoles": [
                    f"@{service_id}",
                ],
                "semantic": "AllOf",
            },
            tags,
        )

    async def create_router_policy(
        self,
        name: str,
        identity_id: str,
        tags: Tags | None = None,
    ) -> str:
        return await self.create(
            "/edge-router-policies",
            {
                "name": name,
                "edgeRouterRoles": ["#all"],
                "identityRoles": [f"@{identity_id}"],
                "semantic": "AllOf",
            },
            tags,
        )

    async def search_service_router_policy(self, id_or_name: str) -> dict[str, Any] | None:
        return await self.search_by_id_or_name("/service-edge-router-policies", id_or_name)

    async def search_router_policy(self, id_or_name: str) -> dict[str, Any] | None:
        return await self.search_by_id_or_name("/edge-router-policies", id_or_name)

    async def delete_service_router_policy(self, policy_id: str) -> None:
        return await self.delete("/service-edge-router-policies", policy_id)

    async def delete_router_policy(self, policy_id: str) -> None:
        return await self.delete("/edge-router-policies", policy_id)

    async def search_service(self, id_or_name: str) -> dict[str, Any] | None:
        return await self.search_by_id_or_name("/services", id_or_name)

    async def get_service(self, service_id: str) -> dict[str, Any]:
        return await self.get("/services", service_id)

    async def delete_service(self, service_id: str) -> None:
        return await self.delete("/services", service_id)

    async def create_user_identity(self, name: str, tags: Tags | None = None) -> str:
        return await self._create_identity(name, "User", tags=tags)

    async def create_device_identity(self, name: str, tags: Tags | None = None) -> str:
        return await self._create_identity(name, "Device", tags=tags)

    async def search_identity(self, id_or_name: str) -> dict[str, Any] | None:
        return await self.search_by_id_or_name("/identities", id_or_name)

    async def search_config_type(self, id_or_name: str) -> dict[str, Any] | None:
        return await self.search_by_id_or_name("/config-types", id_or_name)

    async def delete_config_type(self, config_type_id: str) -> None:
        return await self.delete("/config-types", config_type_id)

    async def get_identity(self, identity_id: str) -> dict[str, Any]:
        return await self.get("/identities", identity_id)

    async def delete_identity(self, identity_id: str) -> None:
        return await self.delete("/identities", identity_id)

    async def fetch_ca_certificates(self) -> str:
        response = await self.httpx_client.get("/.well-known/est/cacerts")
        response.raise_for_status()
        return response.text

    async def create_dial_service_policy(
        self, name: str, service_id: str, identity_id: str, tags: Tags | None = None
    ) -> str:
        return await self._create_service_policy("Dial", name, service_id, identity_id, tags)

    async def create_bind_service_policy(
        self, name: str, service_id: str, identity_id: str, tags: Tags | None = None
    ) -> str:
        return await self._create_service_policy("Bind", name, service_id, identity_id, tags)

    async def search_service_policy(self, id_or_name: str) -> dict[str, Any] | None:
        return await self.search_by_id_or_name("/service-policies", id_or_name)

    async def delete_service_policy(self, policy_id: str) -> None:
        return await self.delete("/service-policies", policy_id)

    async def _create_service_policy(
        self,
        type: Literal["Dial", "Bind"],
        name: str,
        service_id: str,
        identity_id: str,
        tags: Tags | None = None,
    ) -> str:
        return await self.create(
            "/service-policies",
            {
                "name": name,
                "type": type,
                "serviceRoles": [f"@{service_id}"],
                "identityRoles": [f"@{identity_id}"],
                "semantic": "AllOf",
            },
            tags,
        )

    async def _create_identity(
        self,
        name: str,
        type: Literal["User", "Device", "Default"],
        tags: Tags | None = None,
    ) -> str:
        return await self.create(
            "/identities",
            {
                "name": name,
                "type": type,
                "isAdmin": False,
                "enrollment": {"ott": True},
            },
            tags,
        )


class ZitiClientAPI(BaseZitiAPI):
    @property
    def base_url(self):
        return f"{self.settings.ziti.api.client}/edge/client/v1"

    async def enroll_identity(self, jti: str, csr_pem: str) -> dict[str, Any]:
        response = await self.httpx_client.post(
            "/enroll",
            params={
                "method": "ott",
                "token": jti,
            },
            headers={"Content-Type": "application/x-pem-file"},
            content=csr_pem,
        )
        response.raise_for_status()
        return response.json()
