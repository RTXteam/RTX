# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from typing import Any, Dict, List


class BaseExampleQuestionsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseExampleQuestionsApi.subclasses = BaseExampleQuestionsApi.subclasses + (cls,)
    async def example_questions(
        self,
    ) -> List[object]:
        ...
