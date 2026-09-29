# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from typing import Any
from saas_identity_platform_fastapi.models.login_request import LoginRequest
from saas_identity_platform_fastapi.models.login_response import LoginResponse
from saas_identity_platform_fastapi.models.sessions_login_default_response import SessionsLoginDefaultResponse


class BaseAuthApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAuthApi.subclasses = BaseAuthApi.subclasses + (cls,)
    async def sessions_login(
        self,
        login_request: LoginRequest,
    ) -> LoginResponse:
        ...


    async def sessions_logout(
        self,
    ) -> None:
        ...
