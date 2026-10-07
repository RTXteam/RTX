# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any
from typing_extensions import Annotated
from openapi_server.models.mesh_ngd_response import MeshNgdResponse


class BasePubmedMeshNgdApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BasePubmedMeshNgdApi.subclasses = BasePubmedMeshNgdApi.subclasses + (cls,)
    async def pubmed_mesh_ngd(
        self,
        term1: Annotated[StrictStr, Field(description="First of two terms. Order not important.")],
        term2: Annotated[StrictStr, Field(description="Second of two terms. Order not important.")],
    ) -> MeshNgdResponse:
        ...
