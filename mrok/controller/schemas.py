from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)

from mrok.conf import get_settings
from mrok.types.ziti import Tags


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    tags: Tags | None = None


class IdSchema(BaseModel):
    id: str


class ExtensionIdSchema(BaseModel):
    id: Annotated[str, Field(pattern=get_settings().identifiers.extension.regex)]


# For instance
class InstanceIdSchema(BaseModel):
    id: Annotated[str, Field(pattern=get_settings().identifiers.instance.regex)]


class ExtensionBase(BaseSchema):
    extension: ExtensionIdSchema


class ExtensionRead(BaseSchema, IdSchema):
    name: str
    instances: list[InstanceRead] | None = None

    @computed_field
    def extension(self) -> dict:
        return {"id": self.name.upper()}


class ExtensionCreate(ExtensionBase):
    pass


class InstanceBase(BaseSchema):
    instance: InstanceIdSchema


class InstanceRead(BaseSchema, IdSchema):
    name: str
    identity: dict[str, Any] | None = None
    has_edge_router_connection: bool | None = Field(
        False,
        alias="hasEdgeRouterConnection",
        exclude=True,
    )

    @computed_field
    def instance(self) -> dict:
        if "." not in self.name:
            instance_id = self.name
        else:
            instance_id, _ = self.name.split(".", 1)
        return {"id": instance_id.upper()}

    @computed_field
    def extension(self) -> dict:
        if "." not in self.name:
            extension_id = self.tags["mrok-service"]  # type: ignore
        else:
            _, extension_id = self.name.split(".", 1)

        return {"id": extension_id.upper()}  # type: ignore

    @computed_field
    def status(self) -> Literal["online", "offline"]:
        return "online" if bool(self.has_edge_router_connection) else "offline"


class InstanceCreate(InstanceBase):
    pass
