from __future__ import annotations

from decimal import Decimal
from html import escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession
from app.models import Sale, Shop
from app.services.permissions import require_permission
from app.permissions import Permission
from app.services.products import parse_uuid


router = APIRouter(
    prefix="/receipts",
    tags=["Receipts"],
)


def money(value) -> str:
    return f"{Decimal(value or 0):,.2f}"


@router.get(
    "/{sale_id}/print",
    response_class=HTMLResponse,
)
async def print_receipt(
    sale_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.SALES,
    )

    sale_uuid = parse_uuid(
        sale_id,
        "sale_id",
    )

    result = await db.execute(
        select(Sale)
        .options(
            selectinload(Sale.items),
            selectinload(Sale.payments),
        )
        .where(
            Sale.id == sale_uuid,
            Sale.shop_id == current_user.shop_id,
        )
    )

    sale = result.scalar_one_or_none()

    if sale is None:
        raise HTTPException(
            status_code=404,
            detail="Sale not found.",
        )

    shop = await db.scalar(
        select(Shop).where(
            Shop.id == current_user.shop_id,
        )
    )

    if shop is None:
        raise HTTPException(
            status_code=404,
            detail="Shop not found.",
        )

    width = (
        "58mm"
        if str(shop.receipt_width).lower().startswith("58")
        else "80mm"
    )

    logo = ""

    if shop.logo_url:
        logo = (
            f'<img class="logo" '
            f'src="{escape(shop.logo_url)}" '
            f'alt="Shop logo">'
        )

    item_rows = ""

    for item in sale.items:
        item_rows += f"""
        <tr>
            <td colspan="2">
                <strong>{escape(item.product_name)}</strong>
            </td>
        </tr>
        <tr>
            <td>
                {item.quantity:g} × {money(item.unit_price)}
            </td>
            <td class="right">
                {money(item.total)}
            </td>
        </tr>
        """

    payment_rows = ""

    for payment in sale.payments:
        payment_rows += f"""
        <tr>
            <td>{escape(str(payment.method))}</td>
            <td class="right">{money(payment.amount)}</td>
        </tr>
        """

    html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{escape(sale.receipt_number)}</title>
<style>
@page {{
    size: {width} auto;
    margin: 0;
}}

* {{
    box-sizing: border-box;
}}

html, body {{
    margin: 0;
    padding: 0;
    background: white;
}}

body {{
    width: {width};
    font-family: Arial, Helvetica, sans-serif;
    color: #000;
    font-size: 11px;
    line-height: 1.35;
}}

.receipt {{
    width: 100%;
    padding: 5mm 3mm;
}}

.center {{
    text-align: center;
}}

.right {{
    text-align: right;
}}

.logo {{
    max-width: 35mm;
    max-height: 18mm;
    object-fit: contain;
    margin-bottom: 4px;
}}

.shop-name {{
    font-size: 17px;
    font-weight: 800;
}}

.shop-info {{
    font-size: 9px;
}}

.divider {{
    border-top: 1px dashed #000;
    margin: 7px 0;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

td {{
    padding: 2px 0;
    vertical-align: top;
}}

.summary td {{
    padding: 2px 0;
}}

.total {{
    font-size: 15px;
    font-weight: 800;
}}

.footer {{
    margin-top: 10px;
    text-align: center;
    font-size: 9px;
}}

@media print {{
    .no-print {{
        display: none !important;
    }}
}}
</style>
</head>

<body onload="window.print()">
<div class="receipt">

    <div class="center">
        {logo}
        <div class="shop-name">
            {escape(shop.name)}
        </div>

        <div class="shop-info">
            {escape(shop.address or "")}
        </div>

        <div class="shop-info">
            {escape(shop.phone or "")}
        </div>
    </div>

    <div class="divider"></div>

    <table>
        <tr>
            <td>Receipt</td>
            <td class="right">
                {escape(sale.receipt_number)}
            </td>
        </tr>

        <tr>
            <td>Date</td>
            <td class="right">
                {sale.created_at.strftime("%d-%m-%Y %I:%M %p")}
            </td>
        </tr>
    </table>

    <div class="divider"></div>

    <table>
        {item_rows}
    </table>

    <div class="divider"></div>

    <table class="summary">
        <tr>
            <td>Subtotal</td>
            <td class="right">{money(sale.subtotal)}</td>
        </tr>

        <tr>
            <td>Discount</td>
            <td class="right">-{money(sale.discount)}</td>
        </tr>

        <tr>
            <td class="total">TOTAL</td>
            <td class="right total">{money(sale.total)}</td>
        </tr>
    </table>

    <div class="divider"></div>

    <table>
        {payment_rows}
    </table>

    <div class="divider"></div>

    <table>
        <tr>
            <td>Paid</td>
            <td class="right">{money(sale.paid_amount)}</td>
        </tr>

        <tr>
            <td>Credit</td>
            <td class="right">{money(sale.credit_amount)}</td>
        </tr>
    </table>

    <div class="divider"></div>

    <div class="footer">
        {escape(shop.receipt_footer or "Thank you for shopping with us.")}
    </div>

</div>
</body>
</html>
"""

    return HTMLResponse(content=html)
