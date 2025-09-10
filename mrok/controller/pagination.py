from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import Query
from fastapi_pagination.bases import AbstractPage, AbstractParams, RawParams
from pydantic import BaseModel, Field

from mrok.controller.schemas import BaseSchema


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
        return RawParams(
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
        assert isinstance(params, LimitOffsetParams)
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
