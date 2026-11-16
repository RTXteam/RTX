# coding: utf-8

import sys

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any, Dict, List
from typing_extensions import Annotated

from openapi_server.models.entity_query import EntityQuery

from openapi_server.apis.entity_api_base import BaseEntityApi

from node_synonymizer import NodeSynonymizer

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


class ImplEntityApi(BaseEntityApi):

    async def get_entity(
        self,
        q: Annotated[List[StrictStr], Field(description="A string to search by (name, abbreviation, CURIE, etc.). The parameter may be repeated for multiple search strings.")],
    ) -> object:

        synonymizer = NodeSynonymizer()
        response = synonymizer.get_normalizer_results(q)
        return response


    async def post_entity(
        self,
        body: Annotated[Dict[str, Any], Field(description="List of terms to get information about")],
    ) -> object:

        synonymizer = NodeSynonymizer()
        response = synonymizer.get_normalizer_results(body.to_dict())
        return response

