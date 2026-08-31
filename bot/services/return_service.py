from datetime import datetime, timezone

from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import OperationFailure

from bot.services.user_service import calculate_commission
from bot.services.wallet_service import WalletService
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
    def __init__(self, db, wallet_service: WalletService | None = None):
        self.db = db
        self.orders = db["orders"]
        self.returns = db["product_returns"]
        self.tracking_codes = db["product_tracking_codes"]
        self.counters = db["counters"]
        self.wallet_service = wallet_service or WalletService(db)
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.tracking_codes.create_index("tracking_code", unique=True)
        self.returns.create_index("return_id", unique=True)
        self.returns.create_index("tracking_code")
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

    def create_return(self, seller: dict, draft: dict, admin_telegram_id: int | None = None) -> dict:
        tracking_code = normalize_digits(draft["tracking_code"])
        return_type = draft["return_type"]
        if return_type not in RETURN_STATUS_BY_TYPE:
            raise ProductReturnError("invalid return type")

        session = self.db.client.start_session()
        try:
            with session.start_transaction():
                return self._create_return_in_transaction(
                    seller,
                    draft,
                    tracking_code,
                    return_type,
                    admin_telegram_id,
                    session=session,
                )
        except OperationFailure as exc:
            if exc.code != 20:
                raise
            return self._create_return_without_transaction(
                seller,
                draft,
                tracking_code,
                return_type,
                admin_telegram_id,
            )
        finally:
            session.end_session()

    def _load_return_context(self, seller: dict, tracking_code: str, session=None) -> tuple[dict, dict, dict, int]:
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

        commission_amount = int(unit.get("commission_amount") or 0)
        if commission_amount <= 0:
            commission_amount = calculate_commission(order.get("product_price", 0))
        return tracking, order, unit, commission_amount

    def _return_document(
        self,
        seller: dict,
        draft: dict,
        tracking: dict,
        return_type: str,
        commission_amount: int,
        return_id: str,
        wallet_transaction_id: str,
        now: str,
    ) -> dict:
        jalali_date, jalali_month, tehran_time = jalali_datetime_parts(now)
        return {
            "return_id": return_id,
            "order_id": tracking["order_id"],
            "unit_index": int(tracking["unit_index"]),
            "tracking_code": normalize_digits(draft["tracking_code"]),
            "product_key": tracking.get("product_key", ""),
            "product_code": tracking.get("product_code", ""),
            "product_name": tracking.get("product_name", ""),
            "quantity": int(draft.get("quantity", 1)),
            "return_type": return_type,
            "return_type_label": RETURN_TYPE_LABELS_FA[return_type],
            "store_code": str(seller["store_code"]),
            "seller_telegram_id": int(seller["telegram_id"]),
            "invoice_image_path": draft["invoice_image_path"],
            "commission_amount": commission_amount,
            "wallet_transaction_id": wallet_transaction_id,
            "created_at": now,
            "jalali_date": jalali_date,
            "jalali_month": jalali_month,
            "tehran_time": tehran_time,
        }

    def _create_return_in_transaction(
        self,
        seller: dict,
        draft: dict,
        tracking_code: str,
        return_type: str,
        admin_telegram_id: int | None,
        session,
    ) -> dict:
        tracking, _order, _unit, commission_amount = self._load_return_context(seller, tracking_code, session=session)
        return_id = self._next_return_id(session=session)
        wallet_transaction_id = f"wallet:return:{return_id}:{tracking_code}"
        now = utc_now()
        document = self._return_document(
            seller, draft, tracking, return_type, commission_amount, return_id, wallet_transaction_id, now
        )
        self.returns.insert_one(document, session=session)
        self._mark_tracking_returned(tracking_code, return_type, now, session=session)
        transaction, _applied = self._debit_return_commission(
            seller, tracking, commission_amount, return_id, wallet_transaction_id, admin_telegram_id, session=session
        )
        document["wallet_balance_after"] = transaction.get("balance_after")
        document.pop("_id", None)
        return document

    def _create_return_without_transaction(
        self,
        seller: dict,
        draft: dict,
        tracking_code: str,
        return_type: str,
        admin_telegram_id: int | None,
    ) -> dict:
        tracking, _order, _unit, commission_amount = self._load_return_context(seller, tracking_code)
        if self.wallet_service.get_balance(seller["telegram_id"]) < commission_amount:
            raise ValueError("insufficient balance or user not found")

        return_id = self._next_return_id()
        wallet_transaction_id = f"wallet:return:{return_id}:{tracking_code}"
        now = utc_now()
        document = self._return_document(
            seller, draft, tracking, return_type, commission_amount, return_id, wallet_transaction_id, now
        )
        self.returns.insert_one(document)
        try:
            self._mark_tracking_returned(tracking_code, return_type, now)
            transaction, _applied = self._debit_return_commission(
                seller, tracking, commission_amount, return_id, wallet_transaction_id, admin_telegram_id
            )
        except Exception:
            self.tracking_codes.update_one(
                {"tracking_code": tracking_code, "status": RETURN_STATUS_BY_TYPE[return_type]},
                {"$set": {"status": "sold", "returned_at": None, "updated_at": utc_now()}},
            )
            self.returns.delete_one({"return_id": return_id})
            raise
        document["wallet_balance_after"] = transaction.get("balance_after")
        document.pop("_id", None)
        return document

    def _mark_tracking_returned(self, tracking_code: str, return_type: str, now: str, session=None) -> None:
        updated_tracking = self.tracking_codes.update_one(
            {"tracking_code": tracking_code, "status": "sold"},
            {
                "$set": {
                    "status": RETURN_STATUS_BY_TYPE[return_type],
                    "returned_at": now,
                    "updated_at": now,
                }
            },
            session=session,
        )
        if updated_tracking.modified_count != 1:
            raise ProductReturnError("tracking already returned")

    def _debit_return_commission(
        self,
        seller: dict,
        tracking: dict,
        commission_amount: int,
        return_id: str,
        wallet_transaction_id: str,
        admin_telegram_id: int | None,
        session=None,
    ) -> tuple[dict, bool]:
        return self.wallet_service.apply_transaction(
            telegram_id=seller["telegram_id"],
            store_code=seller["store_code"],
            transaction_type="debit",
            source="product_return",
            amount=commission_amount,
            description=f"کسر پورسانت بابت مرجوعی کالای {tracking.get('product_name', '')}",
            transaction_id=wallet_transaction_id,
            admin_telegram_id=admin_telegram_id,
            extra_fields={
                "related_order_id": tracking["order_id"],
                "related_return_id": return_id,
                "tracking_code": tracking["tracking_code"],
            },
            session=session,
        )

    def _next_return_id(self, session=None) -> str:
        counter = self.counters.find_one_and_update(
            {"_id": "product_returns"},
            {"$inc": {"sequence": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        return f"RET-{int(counter['sequence']):06d}"
