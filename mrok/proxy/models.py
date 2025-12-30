from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import core_schema


class X509Credentials(BaseModel):
    key: str
    cert: str
    ca: str

    @field_validator("key", "cert", "ca", mode="before")
    @classmethod
    def strip_pem_prefix(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("pem:"):
            return value[4:]
        return value


class ServiceMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    identity: str
    extension: str
    instance: str
    domain: str | None = None
    tags: dict[str, str | bool | None] | None = None


class Identity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    zt_api: str = Field(validation_alias="ztAPI")
    id: X509Credentials
    zt_apis: str | None = Field(default=None, validation_alias="ztAPIs")
    config_types: str | None = Field(default=None, validation_alias="configTypes")
    enable_ha: bool = Field(default=False, validation_alias="enableHa")
    mrok: ServiceMetadata | None = None

    @staticmethod
    def load_from_file(path: str | Path) -> Identity:
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return Identity.model_validate(data)


class FixedSizeByteBuffer:
    def __init__(self, max_size: int):
        self._max_size = max_size
        self._buf = bytearray()
        self.overflow = False

    def write(self, data: bytes) -> None:
        if not data:
            return

        remaining = self._max_size - len(self._buf)
        if remaining <= 0:
            self.overflow = True
            return

        if len(data) > remaining:
            self._buf.extend(data[:remaining])
            self.overflow = True
        else:
            self._buf.extend(data)

    def getvalue(self) -> bytes:
        return bytes(self._buf)

    def clear(self) -> None:
        self._buf.clear()
        self.overflow = False


class HTTPHeaders(dict):
    def __init__(self, initial=None):
        super().__init__()
        if initial:
            for k, v in initial.items():
                super().__setitem__(str(k).lower(), str(v))

    def __getitem__(self, key: str) -> str:
        return super().__getitem__(key.lower())

    def __setitem__(self, key: str, value: str) -> None:
        super().__setitem__(str(key).lower(), str(value))

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key.lower())

    def get(self, k, default=None):
        return super().get(k.lower(), default)

    @classmethod
    def from_asgi(cls, items: list[tuple[bytes, bytes]]) -> HTTPHeaders:
        d = {k.decode("latin-1"): v.decode("latin-1") for k, v in items}
        return cls(d)

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        """Provide a pydantic-core schema so Pydantic treats this as a mapping of str->str.

        We generate the schema for `dict[str, str]` using the provided handler and wrap
        it with a validator that converts the validated dict into `HTTPHeaders`.
        """
        # handler may be a callable or an object with `generate_schema`; handle both
        try:
            dict_schema = handler.generate_schema(dict[str, str])
        except AttributeError:
            dict_schema = handler(dict[str, str])

        def _wrap(v, validator):
            # `validator` will validate input according to `dict_schema` and return a dict
            validated = validator(input_value=v)
            if isinstance(validated, HTTPHeaders):
                return validated
            return cls(validated)

        return core_schema.no_info_wrap_validator_function(
            _wrap,
            dict_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(lambda v: dict(v)),
        )


class HTTPRequest(BaseModel):
    method: str
    url: str
    headers: HTTPHeaders
    query_string: bytes
    start_time: float
    body: bytes | None = None
    body_truncated: bool | None = None


class HTTPResponse(BaseModel):
    type: Literal["response"] = "response"
    request: HTTPRequest
    status: int
    headers: HTTPHeaders
    duration: float
    body: bytes | None = None
    body_truncated: bool | None = None


class ProcessMetrics(BaseModel):
    cpu: float
    mem: float


class DataTransferMetrics(BaseModel):
    bytes_in: int
    bytes_out: int


class RequestsMetrics(BaseModel):
    rps: int
    total: int
    successful: int
    failed: int


class ResponseTimeMetrics(BaseModel):
    avg: float
    min: int
    max: int
    p50: int
    p90: int
    p99: int


class WorkerMetrics(BaseModel):
    worker_id: str
    data_transfer: DataTransferMetrics
    requests: RequestsMetrics
    response_time: ResponseTimeMetrics
    process: ProcessMetrics


class Status(BaseModel):
    type: Literal["status"] = "status"
    meta: ServiceMetadata
    metrics: WorkerMetrics


class Event(BaseModel):
    type: Literal["status", "response"]
    data: Status | HTTPResponse = Field(discriminator="type")
