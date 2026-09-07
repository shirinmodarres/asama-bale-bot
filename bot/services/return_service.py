from datetime import datetime, timezone

from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from bot.utils.datetime_format import jalali_datetime_parts
from bot.utils.normalize import normalize_digits


RETURN_STATUS_BY_TYPE = {
    "resellable": "returned_resellable",
    "defective": "returned_defective",
}

RETURN_TYPE_LABELS_FA = {
    "resellable": "اکبند / قابل فروش",
    "defective": "معیوب / غیرقابل فروش",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProductReturnError(Exception):
    pass


class ProductReturnService:
    def __init__(self, db, commission_service=None):
        self.db = db
        self.orders = db["orders"]
        self.returns = db["product_returns"]
        self.tracking_codes = db["product_tracking_codes"]
        self.counters = db["counters"]
        self.commission_service = commission_service
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.tracking_codes.create_index("tracking_code", unique=True)
        self.returns.create_index("return_id", unique=True)
        self.returns.create_index("tracking_code")
        self.returns.create_index([("status", ASCENDING), ("store_code", ASCENDING), ("requested_at", ASCENDING)])
        self.returns.create_index([("seller_telegram_id", ASCENDING), ("created_at", ASCENDING)])
        self.returns.create_index([("store_code", ASCENDING), ("created_at", ASCENDING)])

    def list_sold_items_for_seller(self, seller: dict) -> list[dict]:
        items = list(
            self.tracking_codes.find(
                {
                    "seller_telegram_id": int(seller["telegram_id"]),
                    "store_code": str(seller["store_code"]),
                    "status": "sold",
                },
                {"_id": 0},
            ).sort("sold_at", -1)
        )
        return items

    def list_returnable_products_for_seller(self, seller: dict) -> list[dict]:
        products = list(
            self.tracking_codes.aggregate(
                [
                    {
                        "$match": {
                            "seller_telegram_id": int(seller["telegram_id"]),
                            "store_code": str(seller["store_code"]),
                            "status": "sold",
                        }
                    },
                    {
                        "$group": {
                            "_id": {
                                "product_key": "$product_key",
                                "product_code": "$product_code",
                            },
                            "product_key": {"$first": "$product_key"},
                            "product_code": {"$first": "$product_code"},
                            "product_name": {"$first": "$product_name"},
                            "sold_count": {"$sum": 1},
                        }
                    },
                    {"$sort": {"product_name": 1}},
                ]
            )
        )
        for product in products:
            product.pop("_id", None)
        return products

    def get_sold_tracking_for_seller(self, seller: dict, tracking_code: str) -> dict | None:
        return self.tracking_codes.find_one(
            {
                "tracking_code": normalize_digits(tracking_code),
                "seller_telegram_id": int(seller["telegram_id"]),
                "store_code": str(seller["store_code"]),
                "status": "sold",
            },
            {"_id": 0},
        )

    def get_sold_tracking_for_seller_product(
        self,
        seller: dict,
        tracking_code: str,
        product_key: str,
        product_code: str,
    ) -> dict | None:
        tracking = self.get_sold_tracking_for_seller(seller, tracking_code)
        if not tracking:
            return None
        if product_key and tracking.get("product_key") != product_key:
            return None
        if not product_key and product_code and tracking.get("product_code") != product_code:
            return None
        return tracking

    def create_return_request(self, seller: dict, draft: dict) -> dict:
        tracking_code = normalize_digits(draft["tracking_code"])
        return_type = draft["return_type"]
        if return_type not in RETURN_STATUS_BY_TYPE:
            raise ProductReturnError("invalid return type")

        tracking, order, unit = self._load_return_context(seller, tracking_code)
        if self.returns.find_one(
            {
                "order_id": tracking["order_id"],
                "unit_index": int(tracking["unit_index"]),
                "status": {"$in": ["pending", "approved"]},
            },
            {"_id": 1},
        ):
            raise ProductReturnError("duplicate return")
        return_id = self._next_return_id()
        now = utc_now()
        document = self._return_document(seller, draft, tracking, order, unit, return_type, return_id, now)
        try:
            self.returns.insert_one(document)
        except DuplicateKeyError:
            raise ProductReturnError("duplicate return")
        document.pop("_id", None)
        return document

    def create_return(self, seller: dict, draft: dict, admin_telegram_id: int | None = None) -> dict:
        return self.create_return_request(seller, draft)

    def get_return(self, return_id: str) -> dict | None:
        return self.returns.find_one({"return_id": return_id}, {"_id": 0})

    def list_pending_for_stores(self, store_codes: set[str]) -> list[dict]:
        return list(
            self.returns.find(
                {
                    "status": "pending",
                    "store_code": {"$in": [str(code) for code in store_codes]},
                },
                {"_id": 0},
            ).sort("requested_at", 1)
        )

    def approve_return(self, return_id: str, expert_telegram_id: int) -> dict:
        product_return = self.returns.find_one({"return_id": return_id, "status": "pending"})
        if not product_return:
            raise ProductReturnError("return is not pending")

        now = utc_now()
        tracking_code = product_return["tracking_code"]
        updated_tracking = self.tracking_codes.update_one(
            {"tracking_code": tracking_code, "status": "sold"},
            {
                "$set": {
                    "status": RETURN_STATUS_BY_TYPE[product_return["return_type"]],
                    "returned_at": now,
                    "updated_at": now,
                }
            },
        )
        if updated_tracking.modified_count != 1:
            raise ProductReturnError("tracking is not sold")

        updated_return = self.returns.find_one_and_update(
            {"return_id": return_id, "status": "pending"},
            {
                "$set": {
                    "status": "approved",
                    "reviewed_at": now,
                    "reviewed_by": int(expert_telegram_id),
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated_return:
            self.tracking_codes.update_one(
                {"tracking_code": tracking_code, "status": RETURN_STATUS_BY_TYPE[product_return["return_type"]]},
                {"$set": {"status": "sold", "returned_at": None, "updated_at": utc_now()}},
            )
            raise ProductReturnError("return already reviewed")

        try:
            if self.commission_service:
                updated_return["commission_performance"] = self.commission_service.recalculate_for_return(updated_return)
        except Exception:
            self.returns.update_one(
                {"return_id": return_id},
                {"$set": {"status": "pending", "reviewed_at": None, "reviewed_by": None, "updated_at": utc_now()}},
            )
            self.tracking_codes.update_one(
                {"tracking_code": tracking_code, "status": RETURN_STATUS_BY_TYPE[product_return["return_type"]]},
                {"$set": {"status": "sold", "returned_at": None, "updated_at": utc_now()}},
            )
            raise

        updated_return.pop("_id", None)
        return updated_return

    def reject_return(self, return_id: str, expert_telegram_id: int, rejection_reason: str) -> dict:
        now = utc_now()
        product_return = self.returns.find_one_and_update(
            {"return_id": return_id, "status": "pending"},
            {
                "$set": {
                    "status": "rejected",
                    "reviewed_at": now,
                    "reviewed_by": int(expert_telegram_id),
                    "rejection_reason": rejection_reason,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not product_return:
            raise ProductReturnError("return is not pending")
        product_return.pop("_id", None)
        return product_return

    def _load_return_context(self, seller: dict, tracking_code: str, session=None) -> tuple[dict, dict, dict]:
        tracking = self.tracking_codes.find_one(
            {
                "tracking_code": tracking_code,
                "seller_telegram_id": int(seller["telegram_id"]),
                "store_code": str(seller["store_code"]),
                "status": "sold",
            },
            session=session,
        )
        if not tracking:
            raise ProductReturnError("tracking is not sold")

        order = self.orders.find_one({"id": tracking["order_id"]}, session=session)
        if not order:
            raise ProductReturnError("order not found")

        unit = next(
            (
                item
                for item in order.get("units", [])
                if int(item.get("index", 0)) == int(tracking["unit_index"])
            ),
            None,
        )
        if not unit:
            raise ProductReturnError("unit not found")

        return tracking, order, unit

    def _return_document(
        self,
        seller: dict,
        draft: dict,
        tracking: dict,
        order: dict,
        unit: dict,
        return_type: str,
        return_id: str,
        now: str,
    ) -> dict:
        jalali_date, jalali_month, tehran_time = jalali_datetime_parts(now)
        sold_at = tracking.get("sold_at") or unit.get("validation_decision_at") or order.get("updated_at") or order.get("created_at")
        return {
            "return_id": return_id,
            "order_id": tracking["order_id"],
            "unit_index": int(tracking["unit_index"]),
            "tracking_code": normalize_digits(draft["tracking_code"]),
            "product_key": tracking.get("product_key", ""),
            "product_code": tracking.get("product_code", ""),
            "product_name": tracking.get("product_name", ""),
            "product_price": int(unit.get("product_price") or order.get("product_price") or 0),
            "quantity": int(draft.get("quantity", 1)),
            "return_type": return_type,
            "return_type_label": RETURN_TYPE_LABELS_FA[return_type],
            "store_code": str(seller["store_code"]),
            "seller_telegram_id": int(seller["telegram_id"]),
            "invoice_image_path": draft["invoice_image_path"],
            "status": "pending",
            "requested_at": now,
            "reviewed_at": None,
            "reviewed_by": None,
            "rejection_reason": None,
            "sold_at": sold_at,
            "sale_month": jalali_datetime_parts(sold_at)[1] if sold_at else jalali_month,
            "created_at": now,
            "jalali_date": jalali_date,
            "jalali_month": jalali_month,
            "tehran_time": tehran_time,
            "updated_at": now,
        }

    def _next_return_id(self, session=None) -> str:
        counter = self.counters.find_one_and_update(
            {"_id": "product_returns"},
            {"$inc": {"sequence": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        return f"RET-{int(counter['sequence']):06d}"
