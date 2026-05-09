import asyncio
from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.enums import CouponStatus, LiveSessionStatus, ProductStatus
from app.db.base import Coupon, LiveSession, LiveSessionProduct, Product, SkuInventory
from app.db.session import SessionLocal


async def seed_database() -> None:
    async with SessionLocal() as session:
        existing = await session.scalar(select(LiveSession).where(LiveSession.id == 1))
        if existing:
            return

        now = datetime.now(timezone.utc)
        starts_at = datetime.combine(now.date(), time(21, 0), timezone.utc)
        ends_at = datetime.combine(now.date(), time(23, 59), timezone.utc)
        live_session = LiveSession(id=1, title="618 爆款家电直播", status=LiveSessionStatus.LIVE.value, started_at=now)
        products = [
            Product(id=1, external_product_id="P1001", name="小熊电饭煲", page_price=Decimal("129"), script_price=Decimal("129"), status=ProductStatus.ACTIVE.value),
            Product(id=2, external_product_id="P1002", name="空气炸锅", page_price=Decimal("199"), script_price=Decimal("199"), status=ProductStatus.SOLD_OUT.value),
            Product(id=3, external_product_id="P1003", name="筋膜枪", page_price=Decimal("129"), script_price=Decimal("99"), status=ProductStatus.ACTIVE.value),
        ]
        session.add(live_session)
        session.add_all(products)
        session.add_all(
            [
                LiveSessionProduct(session_id=1, product_id=1, display_order=1, anchor_alias="1 号链接"),
                LiveSessionProduct(session_id=1, product_id=2, display_order=2, anchor_alias="2 号链接"),
                LiveSessionProduct(session_id=1, product_id=3, display_order=3, anchor_alias="3 号链接"),
                SkuInventory(product_id=1, sku_name="默认规格", available_stock=120),
                SkuInventory(product_id=2, sku_name="默认规格", available_stock=0),
                SkuInventory(product_id=3, sku_name="默认规格", available_stock=80),
                Coupon(
                    id=1,
                    external_coupon_id="C50",
                    name="满 199 减 50",
                    discount_amount=Decimal("50"),
                    threshold_amount=Decimal("199"),
                    status=CouponStatus.NOT_STARTED.value,
                    starts_at=starts_at,
                    ends_at=ends_at,
                ),
            ]
        )
        await session.commit()


def main() -> None:
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
