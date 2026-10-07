from __future__ import annotations

from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Role, Shop, User, UserStatus
from app.security import hash_password


async def bootstrap_application() -> None:
    """
    Create the first shop and owner account when the database is empty.

    This operation is intentionally idempotent. Existing shops and users are
    never overwritten on application restart.
    """

    async with AsyncSessionLocal() as db:
        shop_result = await db.execute(
            select(Shop)
            .order_by(Shop.created_at.asc())
            .limit(1)
        )
        shop = shop_result.scalar_one_or_none()

        if shop is None:
            shop = Shop(
                name=settings.initial_shop_name.strip()
                or "General Store",
                address=settings.initial_shop_address.strip() or None,
                phone=settings.initial_shop_phone.strip() or None,
                email=settings.initial_shop_email.strip() or None,
                currency=settings.default_currency.strip() or "PKR",
                timezone=settings.default_timezone.strip()
                or "Asia/Karachi",
                receipt_width=settings.default_receipt_width,
                receipt_footer=settings.default_receipt_footer.strip()
                or "Thank you for shopping with us!",
                is_active=True,
            )

            db.add(shop)
            await db.flush()

        owner_result = await db.execute(
            select(User).where(
                User.shop_id == shop.id,
                User.username == settings.initial_owner_username.strip(),
            )
        )
        owner = owner_result.scalar_one_or_none()

        if owner is None:
            owner = User(
                shop_id=shop.id,
                username=settings.initial_owner_username.strip(),
                full_name=settings.initial_owner_name.strip()
                or "Store Owner",
                email=settings.initial_owner_email.strip() or None,
                password_hash=hash_password(
                    settings.initial_owner_password
                ),
                role=Role.OWNER.value,
                status=UserStatus.ACTIVE.value,
                is_super_admin=True,
            )

            db.add(owner)

        await db.commit()
