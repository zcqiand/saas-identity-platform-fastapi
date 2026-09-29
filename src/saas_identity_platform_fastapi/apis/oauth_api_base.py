# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from saas_identity_platform_fastapi.models.authorize_code_request import AuthorizeCodeRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.o_auth_authorize200_response import OAuthAuthorize200Response
from saas_identity_platform_fastapi.models.token_request import TokenRequest
from saas_identity_platform_fastapi.models.token_response import TokenResponse


class BaseOauthApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseOauthApi.subclasses = BaseOauthApi.subclasses + (cls,)
    async def o_auth_authorize(
        self,
        authorize_code_request: AuthorizeCodeRequest,
    ) -> OAuthAuthorize200Response:
        ...


    async def o_auth_token(
        self,
        token_request: TokenRequest,
    ) -> TokenResponse:
        ...
