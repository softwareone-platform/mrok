from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import Query
from fastapi_pagination import create_page, resolve_params
from fastapi_pagination.bases import AbstractPage, AbstractParams, RawParams
from pydantic import BaseModel, Field

from mrok.controller.schemas import BaseSchema
from mrok.ziti.api import BaseZitiAPI


class MetaPagination(BaseModel):
    limit: int
    offset: int
    total: int


class Meta(BaseModel):
    pagination: MetaPagination


class LimitOffsetParams(BaseModel, AbstractParams):
    limit: int = Query(50, ge=0, le=1000, description="Page size limit")
    offset: int = Query(0, ge=0, description="Page offset")

    def to_raw_params(self) -> RawParams:
        return RawParams(  # pragma: no cover
            limit=self.limit,
            offset=self.offset,
        )


class LimitOffsetPage[S: BaseSchema](AbstractPage[S]):
    data: list[S]
    meta: Meta = Field(alias="$meta")

    __params_type__ = LimitOffsetParams  # type: ignore

    @classmethod
    def create(
        cls,
        items: Sequence[S],
        params: AbstractParams,
        *,
        total: int | None = None,
        **kwargs: Any,
    ) -> LimitOffsetPage[S]:
        if not isinstance(params, LimitOffsetParams):  # pragma: no cover
            raise TypeError("params must be of type LimitOffsetParams")
        return cls(  # type: ignore
            data=items,
            meta=Meta(
                pagination=MetaPagination(
                    limit=params.limit,
                    offset=params.offset,
                    total=total,
                )
            ),
        )


async def paginate[S: BaseSchema](
    api: BaseZitiAPI,
    endpoint: str,
    schema_cls: type[S],
    extra_params: dict | None = None,
) -> AbstractPage[S]:
    params: LimitOffsetParams = resolve_params()
    page = await api.get_page(endpoint, params.limit, params.offset, extra_params)
    pagination_meta = page["meta"]["pagination"]
    total = pagination_meta["totalCount"]
    return create_page(
        [schema_cls(**item) for item in page["data"]],
        params=params,
        total=total,
    )
