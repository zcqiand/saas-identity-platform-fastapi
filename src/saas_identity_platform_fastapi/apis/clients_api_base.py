# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictStr
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.o_auth_client_public_info import OAuthClientPublicInfo


class BaseClientsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseClientsApi.subclasses = BaseClientsApi.subclasses + (cls,)
    async def clients_get_client(
        self,
        clientId: StrictStr,
    ) -> OAuthClientPublicInfo:
        ...
