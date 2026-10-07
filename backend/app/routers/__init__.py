from __future__ import annotations

from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.catalog import router as catalog_router
from app.routers.held_sales import router as held_sales_router
from app.routers.inventory import router as inventory_router
from app.routers.partners import router as partners_router
from app.routers.products import router as products_router
from app.routers.purchases_returns import router as purchases_returns_router
from app.routers.reports import router as reports_router
from app.routers.receipts import router as receipts_router
from app.routers.sales import router as sales_router
from app.routers.shop import router as shop_router
from app.routers.stock import router as stock_router
from app.routers.statements import router as statements_router
from app.routers.users import router as users_router


api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(shop_router)
api_router.include_router(catalog_router)
api_router.include_router(products_router)
api_router.include_router(partners_router)
api_router.include_router(inventory_router)
api_router.include_router(stock_router)
api_router.include_router(sales_router)
api_router.include_router(held_sales_router)
api_router.include_router(purchases_returns_router)
api_router.include_router(reports_router)
api_router.include_router(statements_router)
api_router.include_router(receipts_router)
