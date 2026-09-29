# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.client_menus_api_base import BaseClientMenusApi
import saas_identity_platform_fastapi.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from saas_identity_platform_fastapi.models.extra_models import TokenModel  # noqa: F401
from pydantic import StrictStr
from typing import Any, List
from saas_identity_platform_fastapi.models.client_menus_move_sys_menu_request import ClientMenusMoveSysMenuRequest
from saas_identity_platform_fastapi.models.create_sys_menu_request import CreateSysMenuRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.reorder_sys_menu_request import ReorderSysMenuRequest
from saas_identity_platform_fastapi.models.sys_menu import SysMenu
from saas_identity_platform_fastapi.models.update_sys_menu_request import UpdateSysMenuRequest


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/clients/{clientId}/menus",
    responses={
        200: {"model": List[SysMenu], "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["client-menus"],
    response_model_by_alias=True,
)
async def client_menus_list_sys_menus(
    clientId: StrictStr = Path(..., description=""),
) -> List[SysMenu]:
    if not BaseClientMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseClientMenusApi.subclasses[0]().client_menus_list_sys_menus(clientId)


@router.post(
    "/api/v1/clients/{clientId}/menus",
    responses={
        200: {"model": SysMenu, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["client-menus"],
    response_model_by_alias=True,
)
async def client_menus_create_sys_menu(
    clientId: StrictStr = Path(..., description=""),
    create_sys_menu_request: CreateSysMenuRequest = Body(None, description=""),
) -> SysMenu:
    if not BaseClientMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseClientMenusApi.subclasses[0]().client_menus_create_sys_menu(clientId, create_sys_menu_request)


@router.get(
    "/api/v1/clients/{clientId}/menus/{menuId}",
    responses={
        200: {"model": SysMenu, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["client-menus"],
    response_model_by_alias=True,
)
async def client_menus_get_sys_menu(
    clientId: StrictStr = Path(..., description=""),
    menuId: StrictStr = Path(..., description=""),
) -> SysMenu:
    if not BaseClientMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseClientMenusApi.subclasses[0]().client_menus_get_sys_menu(clientId, menuId)


@router.delete(
    "/api/v1/clients/{clientId}/menus/{menuId}",
    responses={
        204: {"description": "There is no content to send for this request, but the headers may be useful. "},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["client-menus"],
    response_model_by_alias=True,
)
async def client_menus_delete_sys_menu(
    clientId: StrictStr = Path(..., description=""),
    menuId: StrictStr = Path(..., description=""),
) -> None:
    if not BaseClientMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseClientMenusApi.subclasses[0]().client_menus_delete_sys_menu(clientId, menuId)


@router.patch(
    "/api/v1/clients/{clientId}/menus/{menuId}",
    responses={
        200: {"model": SysMenu, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["client-menus"],
    response_model_by_alias=True,
)
async def client_menus_update_sys_menu(
    clientId: StrictStr = Path(..., description=""),
    menuId: StrictStr = Path(..., description=""),
    update_sys_menu_request: UpdateSysMenuRequest = Body(None, description=""),
) -> SysMenu:
    if not BaseClientMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseClientMenusApi.subclasses[0]().client_menus_update_sys_menu(clientId, menuId, update_sys_menu_request)


@router.patch(
    "/api/v1/clients/{clientId}/menus/{menuId}/parent",
    responses={
        200: {"model": SysMenu, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["client-menus"],
    response_model_by_alias=True,
)
async def client_menus_move_sys_menu(
    clientId: StrictStr = Path(..., description=""),
    menuId: StrictStr = Path(..., description=""),
    client_menus_move_sys_menu_request: ClientMenusMoveSysMenuRequest = Body(None, description=""),
) -> SysMenu:
    if not BaseClientMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseClientMenusApi.subclasses[0]().client_menus_move_sys_menu(clientId, menuId, client_menus_move_sys_menu_request)


@router.put(
    "/api/v1/clients/{clientId}/menus/{menuId}/reorder",
    responses={
        200: {"model": List[SysMenu], "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["client-menus"],
    response_model_by_alias=True,
)
async def client_menus_reorder_sys_menus(
    clientId: StrictStr = Path(..., description=""),
    menuId: StrictStr = Path(..., description=""),
    reorder_sys_menu_request: ReorderSysMenuRequest = Body(None, description=""),
) -> List[SysMenu]:
    if not BaseClientMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseClientMenusApi.subclasses[0]().client_menus_reorder_sys_menus(clientId, menuId, reorder_sys_menu_request)
