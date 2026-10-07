from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DbSession
from app.permissions import Permission
from app.schemas.purchase_return import (
    PurchaseCreate,
    PurchaseResponse,
    ReturnCreate,
    ReturnResponse,
)
from app.services.purchase_returns import (
    create_purchase,
    create_return,
    get_purchase,
    get_return,
)
from app.services.permissions import require_permission


router = APIRouter(
    prefix="",
    tags=["Purchases & Returns"],
)


@router.post(
    "/purchases",
    response_model=PurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_purchase_endpoint(
    payload: PurchaseCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> PurchaseResponse:
    require_permission(
        current_user,
        Permission.CREATE_PURCHASE,
    )

    purchase = await create_purchase(
        db=db,
        shop_id=current_user.shop_id,
        user_id=current_user.id,
        payload=payload,
    )

    return PurchaseResponse.model_validate(purchase)


@router.get(
    "/purchases/{purchase_id}",
    response_model=PurchaseResponse,
)
async def get_purchase_endpoint(
    purchase_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> PurchaseResponse:
    require_permission(
        current_user,
        Permission.VIEW_PURCHASES,
    )

    purchase = await get_purchase(
        db=db,
        shop_id=current_user.shop_id,
        purchase_id=purchase_id,
    )

    if purchase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found.",
        )

    return PurchaseResponse.model_validate(purchase)


@router.post(
    "/returns",
    response_model=ReturnResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_return_endpoint(
    payload: ReturnCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ReturnResponse:
    require_permission(
        current_user,
        Permission.CREATE_RETURN,
    )

    sale_return = await create_return(
        db=db,
        shop_id=current_user.shop_id,
        user_id=current_user.id,
        payload=payload,
    )

    return ReturnResponse.model_validate(sale_return)


@router.get(
    "/returns/{return_id}",
    response_model=ReturnResponse,
)
async def get_return_endpoint(
    return_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ReturnResponse:
    require_permission(
        current_user,
        Permission.VIEW_RETURNS,
    )

    sale_return = await get_return(
        db=db,
        shop_id=current_user.shop_id,
        return_id=return_id,
    )

    if sale_return is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found.",
        )

    return ReturnResponse.model_validate(sale_return)
