from copy import deepcopy
from datetime import datetime, timedelta

from data.static_data import CATEGORIES


class ProductCatalogService:
    def __init__(self, db, ttl_seconds: int = 60):
        self.db = db
        self.products = db["products"]
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: dict | None = None
        self._cache_until: datetime | None = None

    def get_categories(self) -> dict:
        now = datetime.utcnow()
        if self._cache is not None and self._cache_until and now < self._cache_until:
            return deepcopy(self._cache)

        categories = self._load_from_mongo()
        if not categories:
            categories = self._fallback_categories()

        self._cache = categories
        self._cache_until = now + self.ttl
        return deepcopy(categories)

    def list_products(self, active: bool | None = None) -> list[dict]:
        products = []
        for category_key, category in self.get_categories().items():
            for product_key in category.get("products", {}).keys():
                item = self.get_product(category_key, product_key)
                if item is None:
                    continue
                if active is None or item["active"] == active:
                    products.append(item)
        return products

    def get_product(self, category_key: str, product_key: str) -> dict | None:
        category = self.get_categories().get(category_key)
        if not category:
            return None

        product = category.get("products", {}).get(product_key)
        if not product:
            return None

        result = dict(product)
        result["category_key"] = category_key
        result["category_name"] = category["name"]
        result["product_key"] = product_key
        result["active"] = bool(result.get("active", True))
        return result

    def set_product_active(self, category_key: str, product_key: str, active: bool) -> bool:
        if self.get_product(category_key, product_key) is None:
            return False

        result = self.products.update_one(
            {
                "category_key": category_key,
                "$or": [
                    {"product_key": product_key},
                    {"product_code": product_key},
                ],
            },
            {
                "$set": {
                    "is_active": bool(active),
                    "active": bool(active),
                    "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
                }
            }
        )
        if result.matched_count == 0:
            return False
        self.clear_cache()
        return True

    def clear_cache(self) -> None:
        self._cache = None
        self._cache_until = None

    def _load_from_mongo(self) -> dict:
        try:
            documents = list(self.products.find({}))
        except Exception:
            return {}

        if not documents:
            return {}

        categories: dict = {}
        for document in documents:
            category_key = str(document.get("category_key") or "").strip()
            product_key = str(document.get("product_key") or document.get("product_code") or "").strip()
            if not category_key or not product_key:
                continue

            category = categories.setdefault(
                category_key,
                {
                    "name": document.get("category_name") or category_key,
                    "products": {},
                },
            )

            category["products"][product_key] = {
                "name": document.get("product_name") or document.get("name") or product_key,
                "model": document.get("product_model") or document.get("model") or "",
                "code": document.get("product_code") or document.get("code") or product_key,
                "price": document.get("price", 0),
                "active": bool(document.get("is_active", document.get("active", True))),
            }

        return categories

    @staticmethod
    def _fallback_categories() -> dict:
        return deepcopy(CATEGORIES)
