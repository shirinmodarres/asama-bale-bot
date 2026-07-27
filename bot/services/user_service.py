from datetime import datetime, timezone

from bot.data.statuses import ACTIVE, PENDING_SELLER_APPROVAL, SELLER_REJECTED


COMMISSION_PERCENT = 4


def calculate_commission(product_price: int) -> int:
    """Return the seller's commission in whole tomans."""
    return int(product_price) * COMMISSION_PERCENT // 100


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class UserService:
    def __init__(self, db):
        self.collection = db["users"]

    def get_user(self, telegram_id: int):
        return self.collection.find_one(
            {"telegram_id": int(telegram_id)},
            {"_id": 0},
        )

    def get_approved_seller_by_store(self, store_code: str):
        return self.collection.find_one(
            {
                "role": "seller",
                "store_code": str(store_code),
                "status": ACTIVE,
            },
            {"_id": 0},
        )

    def list_active_sellers_for_stores(self, store_codes: set[str]) -> list[dict]:
        sellers = list(
            self.collection.find(
                {
                    "role": "seller",
                    "store_code": {"$in": list(store_codes)},
                    "status": ACTIVE,
                },
                {"_id": 0},
            )
        )

        return sorted(
            sellers,
            key=lambda item: item.get("store_code", ""),
        )

    def save_pending_seller(
        self,
        telegram_id: int,
        store_code: str,
        full_name: str,
        phone: str,
    ) -> dict:

        telegram_id = int(telegram_id)
        now = utc_now()

        existing = self.collection.find_one(
            {"telegram_id": telegram_id}
        ) or {}

        wallet = existing.get(
            "wallet",
            {
                "balance": 0,
                "transactions": [],
            },
        )

        user = {
            "telegram_id": telegram_id,
            "role": "seller",
            "store_code": str(store_code),
            "full_name": full_name,
            "phone": phone,
            "status": PENDING_SELLER_APPROVAL,
            "wallet": wallet,
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }

        self.collection.replace_one(
            {"telegram_id": telegram_id},
            user,
            upsert=True,
        )

        return user

    def approve_seller(self, telegram_id: int):
        return self._set_status(telegram_id, ACTIVE)

    def reject_seller(self, telegram_id: int):
        return self._set_status(telegram_id, SELLER_REJECTED)

    def update_seller_info(
        self,
        telegram_id: int,
        full_name: str | None = None,
        phone: str | None = None,
    ):
        user = self.collection.find_one(
            {"telegram_id": int(telegram_id)}
        )

        if not user:
            return None

        updates = {
            "updated_at": utc_now(),
        }

        if full_name is not None:
            updates["full_name"] = full_name

        if phone is not None:
            updates["phone"] = phone

        self.collection.update_one(
            {"telegram_id": int(telegram_id)},
            {"$set": updates},
        )

        return self.get_user(telegram_id)

    def get_wallet(self, telegram_id: int) -> dict:
        user = self.collection.find_one(
            {"telegram_id": int(telegram_id)}
        )

        if not user:
            return {
                "balance": 0,
                "transactions": [],
            }

        wallet = self._ensure_wallet(user)

        self.collection.update_one(
            {"telegram_id": int(telegram_id)},
            {
                "$set": {
                    "wallet": wallet,
                    "updated_at": utc_now(),
                }
            },
        )

        return wallet

    def credit_wallet(
        self,
        telegram_id: int,
        amount: int,
        transaction_id: str,
        description: str,
    ) -> tuple[dict, bool]:

        user = self.collection.find_one(
            {"telegram_id": int(telegram_id)}
        )

        if not user:
            return {
                "balance": 0,
                "transactions": [],
            }, False

        wallet = self._ensure_wallet(user)

        if any(
            transaction.get("id") == transaction_id
            for transaction in wallet["transactions"]
        ):
            return wallet, False

        now = utc_now()

        wallet["balance"] += amount

        wallet["transactions"].append(
            {
                "id": transaction_id,
                "type": "credit",
                "amount": amount,
                "description": description,
                "created_at": now,
            }
        )

        self.collection.update_one(
            {"telegram_id": int(telegram_id)},
            {
                "$set": {
                    "wallet": wallet,
                    "updated_at": now,
                }
            },
        )

        return wallet, True

    def _set_status(self, telegram_id: int, status: str):
        result = self.collection.update_one(
            {"telegram_id": int(telegram_id)},
            {
                "$set": {
                    "status": status,
                    "updated_at": utc_now(),
                }
            },
        )

        if result.matched_count == 0:
            return None

        return self.get_user(telegram_id)

    def _ensure_wallet(self, user: dict) -> dict:
        wallet = user.setdefault(
            "wallet",
            {
                "balance": 0,
                "transactions": [],
            },
        )

        wallet.setdefault("balance", 0)
        wallet.setdefault("transactions", [])

        return wallet
