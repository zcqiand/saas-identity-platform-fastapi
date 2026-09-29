# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictInt, StrictStr
from typing import Any, Optional
from saas_identity_platform_fastapi.models.admin_clients_list_clients200_response import AdminClientsListClients200Response
from saas_identity_platform_fastapi.models.admin_clients_set_client_status_request import AdminClientsSetClientStatusRequest
from saas_identity_platform_fastapi.models.create_o_auth_client_request import CreateOAuthClientRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.o_auth_client import OAuthClient
from saas_identity_platform_fastapi.models.update_o_auth_client_request import UpdateOAuthClientRequest


class BaseAdminClientsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAdminClientsApi.subclasses = BaseAdminClientsApi.subclasses + (cls,)
    async def admin_clients_list_clients(
        self,
        page: Optional[StrictInt],
        page_size: Optional[StrictInt],
    ) -> AdminClientsListClients200Response:
        ...


    async def admin_clients_create_client(
        self,
        create_o_auth_client_request: CreateOAuthClientRequest,
    ) -> OAuthClient:
        ...


    async def admin_clients_get_client(
        self,
        clientId: StrictStr,
    ) -> OAuthClient:
        ...


    async def admin_clients_delete_client(
        self,
        clientId: StrictStr,
    ) -> None:
        ...


    async def admin_clients_update_client(
        self,
        clientId: StrictStr,
        update_o_auth_client_request: UpdateOAuthClientRequest,
    ) -> OAuthClient:
        ...


    async def admin_clients_set_client_status(
        self,
        clientId: StrictStr,
        admin_clients_set_client_status_request: AdminClientsSetClientStatusRequest,
    ) -> OAuthClient:
        ...
