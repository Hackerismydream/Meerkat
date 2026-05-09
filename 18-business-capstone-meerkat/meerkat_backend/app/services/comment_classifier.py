from app.core.enums import AlertType


def normalize_text(text: str) -> str:
    return text.strip().lower().replace(" ", "")


class CommentClassifier:
    coupon_keywords = ("券", "优惠券", "领不了", "没有券", "券没了", "满减", "50元券", "50 元券", "点进去没有")
    inventory_keywords = ("拍不了", "下不了单", "没库存", "没货", "卖完了", "卖完", "无货", "缺货", "售罄", "库存")
    price_keywords = ("价格不对", "主播说", "页面价", "不是99", "怎么129", "虚假宣传", "99页面")
    link_keywords = ("链接打不开", "点不开", "跳转不了", "链接错了")

    def classify(self, text: str) -> AlertType | None:
        normalized = normalize_text(text)
        if any(keyword.replace(" ", "") in normalized for keyword in self.coupon_keywords):
            return AlertType.COUPON_UNAVAILABLE
        if any(keyword in normalized for keyword in self.inventory_keywords):
            return AlertType.INVENTORY_UNAVAILABLE
        if any(keyword.replace(" ", "") in normalized for keyword in self.price_keywords):
            return AlertType.PRICE_MISMATCH
        if any(keyword in normalized for keyword in self.link_keywords):
            return AlertType.LINK_BROKEN
        return None
