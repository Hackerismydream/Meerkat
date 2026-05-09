import asyncio
from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.enums import CouponStatus, LiveSessionStatus, ProductStatus
from app.db.base import (
    Coupon,
    LiveRoom,
    LiveScript,
    LiveSession,
    LiveSessionProduct,
    Product,
    ProductAlias,
    SkuInventory,
)
from app.db.session import SessionLocal


async def seed_database() -> None:
    async with SessionLocal() as session:
        existing = await session.scalar(select(LiveSession).where(LiveSession.id == 1))
        if existing:
            return

        now = datetime.now(timezone.utc)
        starts_at = datetime.combine(now.date(), time(21, 0), timezone.utc)
        ends_at = datetime.combine(now.date(), time(23, 59), timezone.utc)
        room = LiveRoom(
            id=1,
            name="Owncast 618 直播间",
            owncast_base_url="http://localhost:8080",
            owncast_stream_url="http://localhost:8080/hls/stream.m3u8",
            status="ACTIVE",
            owner_user_id="ops-demo",
        )
        live_session = LiveSession(
            id=1,
            live_room_id=1,
            title="618 爆款家电直播",
            status=LiveSessionStatus.LIVE.value,
            current_product_id=1,
            scheduled_start_at=now,
            started_at=now,
        )
        next_session = LiveSession(
            id=2,
            live_room_id=1,
            title="618 返场复盘直播",
            status=LiveSessionStatus.SCHEDULED.value,
            current_product_id=3,
            scheduled_start_at=now,
        )
        products = [
            Product(id=1, external_product_id="P1001", name="小熊电饭煲", page_price=Decimal("129"), script_price=Decimal("129"), status=ProductStatus.ACTIVE.value),
            Product(id=2, external_product_id="P1002", name="空气炸锅", page_price=Decimal("199"), script_price=Decimal("199"), status=ProductStatus.SOLD_OUT.value),
            Product(id=3, external_product_id="P1003", name="筋膜枪", page_price=Decimal("129"), script_price=Decimal("99"), status=ProductStatus.ACTIVE.value),
            Product(id=4, external_product_id="P1004", name="蓝牙耳机", page_price=Decimal("89"), script_price=Decimal("79"), status=ProductStatus.ACTIVE.value),
            Product(id=5, external_product_id="P1005", name="护眼台灯", page_price=Decimal("159"), script_price=Decimal("159"), status=ProductStatus.ACTIVE.value),
            Product(id=6, external_product_id="P1006", name="电动牙刷", page_price=Decimal("99"), script_price=Decimal("89"), status=ProductStatus.ACTIVE.value),
            Product(id=7, external_product_id="P1007", name="恒温水壶", page_price=Decimal("139"), script_price=Decimal("139"), status=ProductStatus.ACTIVE.value),
            Product(id=8, external_product_id="P1008", name="收纳推车", page_price=Decimal("69"), script_price=Decimal("59"), status=ProductStatus.ACTIVE.value),
        ]
        session.add(room)
        session.add_all([live_session, next_session])
        session.add_all(products)
        session.add_all(
            [
                LiveSessionProduct(session_id=1, product_id=1, display_order=1, anchor_alias="1 号链接"),
                LiveSessionProduct(session_id=1, product_id=2, display_order=2, anchor_alias="2 号链接"),
                LiveSessionProduct(session_id=1, product_id=3, display_order=3, anchor_alias="3 号链接"),
                LiveSessionProduct(session_id=1, product_id=4, display_order=4, anchor_alias="蓝色款"),
                LiveSessionProduct(session_id=1, product_id=5, display_order=5, anchor_alias="护眼灯"),
                LiveSessionProduct(session_id=1, product_id=6, display_order=6, anchor_alias="牙刷"),
                LiveSessionProduct(session_id=1, product_id=7, display_order=7, anchor_alias="水壶"),
                LiveSessionProduct(session_id=1, product_id=8, display_order=8, anchor_alias="收纳车"),
                ProductAlias(product_id=1, session_id=1, alias="1 号链接"),
                ProductAlias(product_id=1, session_id=1, alias="电饭煲"),
                ProductAlias(product_id=2, session_id=1, alias="2 号链接"),
                ProductAlias(product_id=2, session_id=1, alias="空气炸锅"),
                ProductAlias(product_id=3, session_id=1, alias="3 号链接"),
                ProductAlias(product_id=3, session_id=1, alias="筋膜枪"),
                ProductAlias(product_id=4, session_id=1, alias="蓝色款"),
                ProductAlias(product_id=5, session_id=1, alias="护眼灯"),
                ProductAlias(product_id=6, session_id=1, alias="牙刷"),
                ProductAlias(product_id=8, session_id=1, alias="收纳车"),
                SkuInventory(product_id=1, sku_name="默认规格", available_stock=120),
                SkuInventory(product_id=2, sku_name="默认规格", available_stock=0),
                SkuInventory(product_id=3, sku_name="默认规格", available_stock=80),
                SkuInventory(product_id=4, sku_name="蓝色", available_stock=15),
                SkuInventory(product_id=5, sku_name="默认规格", available_stock=60),
                SkuInventory(product_id=6, sku_name="默认规格", available_stock=8),
                SkuInventory(product_id=7, sku_name="默认规格", available_stock=40),
                SkuInventory(product_id=8, sku_name="默认规格", available_stock=35),
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
                Coupon(
                    id=2,
                    external_coupon_id="C20",
                    name="满 99 减 20",
                    discount_amount=Decimal("20"),
                    threshold_amount=Decimal("99"),
                    status=CouponStatus.ACTIVE.value,
                    starts_at=now,
                    ends_at=ends_at,
                    applicable_product_id=3,
                ),
                Coupon(
                    id=3,
                    external_coupon_id="C10",
                    name="无门槛 10 元券",
                    discount_amount=Decimal("10"),
                    threshold_amount=Decimal("0"),
                    status=CouponStatus.ACTIVE.value,
                    starts_at=now,
                    ends_at=ends_at,
                ),
                Coupon(
                    id=4,
                    external_coupon_id="C80",
                    name="满 299 减 80",
                    discount_amount=Decimal("80"),
                    threshold_amount=Decimal("299"),
                    status=CouponStatus.NOT_STARTED.value,
                    starts_at=starts_at,
                    ends_at=ends_at,
                ),
                Coupon(
                    id=5,
                    external_coupon_id="CEXPIRED",
                    name="过期 30 元券",
                    discount_amount=Decimal("30"),
                    threshold_amount=Decimal("129"),
                    status=CouponStatus.EXPIRED.value,
                    starts_at=now,
                    ends_at=now,
                ),
                LiveScript(
                    session_id=1,
                    product_id=3,
                    sequence_no=3,
                    spoken_price=Decimal("99"),
                    spoken_coupon_text="叠券到手 99",
                    selling_points="筋膜枪适合运动后放松。",
                    risk_notes="页面价 129，必须确认券后价再口播。",
                ),
                LiveScript(
                    session_id=2,
                    product_id=3,
                    sequence_no=1,
                    spoken_price=Decimal("99"),
                    spoken_coupon_text="沿用上场返场价",
                    selling_points="返场优先讲解历史高转化商品。",
                    risk_notes="上一场出现价格口径投诉，开播前必须复核。",
                ),
            ]
        )
        await session.commit()


def main() -> None:
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
