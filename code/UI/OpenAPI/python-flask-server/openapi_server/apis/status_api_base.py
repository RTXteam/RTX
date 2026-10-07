# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictInt, StrictStr
from typing import Any, Dict, Optional
from typing_extensions import Annotated


class BaseStatusApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseStatusApi.subclasses = BaseStatusApi.subclasses + (cls,)
    async def get_status(
        self,
        last_n_hours: Annotated[Optional[StrictInt], Field(description="Limit results to the past N hours")],
        id: Annotated[Optional[StrictInt], Field(description="Identifier of the log entry")],
        terminate_pid: Annotated[Optional[StrictInt], Field(description="PID of an ongoing query to terminate")],
        authorization: Annotated[Optional[StrictStr], Field(description="Authorization string required for certain calls to status")],
        mode: Annotated[Optional[StrictStr], Field(description="Switch to control the type of returned status information Possible values are: activity: Show query activity on server [default] smartapi: Summarize Translator endpoints at SmartAPI")],
    ) -> object:
        ...


    async def get_logs(
        self,
        mode: Annotated[Optional[StrictStr], Field(description="Specify the log sending mode")],
    ) -> str:
        ...
