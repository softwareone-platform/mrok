from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)

from mrok.types.ziti import Tags


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    tags: Tags | None = None


class IdSchema(BaseModel):
    id: str


class ExtensionIdSchema(BaseModel):
    id: Annotated[str, Field(pattern=r"EXT-\d{4}-\d{4}")]


# For instance
class InstanceIdSchema(BaseModel):
    id: Annotated[str, Field(pattern=r"INS-\d{4}-\d{4}-\d{4}")]


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
        instance_id, _ = self.name.split(".", 1)
        return {"id": instance_id.upper()}

    @computed_field
    def extension(self) -> dict:
        _, extension_id = self.name.split(".", 1)
        return {"id": extension_id.upper()}

    @computed_field
    def status(self) -> Literal["online", "offline"]:
        return "online" if bool(self.has_edge_router_connection) else "offline"


class InstanceCreate(InstanceBase):
    pass
