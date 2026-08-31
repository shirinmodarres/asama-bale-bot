from datetime import datetime, timezone
from uuid import uuid4

from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from bot.utils.datetime_format import jalali_datetime_parts


SOURCE_LABELS_FA = {
    "commission": "پورسانت",
    "manual_admin": "تغییر دستی ادمین",
    "manual_credit": "شارژ دستی قدیمی",
    "lottery_prize": "جایزه",
    "settlement": "تسویه / ارسال به مالی",
    "product_return": "مرجوعی کالا",
    "legacy": "قدیمی",
}

TYPE_LABELS_FA = {
    "credit": "افزایش",
    "debit": "کاهش",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def jalali_parts(value: str) -> tuple[str, str]:
    jalali_date, jalali_month, _tehran_time = jalali_datetime_parts(value)
    return jalali_date, jalali_month


def transaction_datetime_parts(value: str) -> tuple[str, str, str]:
    return jalali_datetime_parts(value)


def manual_transaction_id(operation: str, telegram_id: int) -> str:
    return f"wallet:{operation}:{telegram_id}:{uuid4().hex}"


class WalletService:
    def __init__(self, db):
        self.users = db["users"]
        self.transactions = db["wallet_transactions"]
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.transactions.create_index("transaction_id", unique=True)
        self.transactions.create_index([("telegram_id", ASCENDING), ("created_at", ASCENDING)])
        self.transactions.create_index([("store_code", ASCENDING), ("created_at", ASCENDING)])
        self.transactions.create_index([("source", ASCENDING), ("created_at", ASCENDING)])

    def get_balance(self, telegram_id: int) -> int:
        user = self.users.find_one({"telegram_id": int(telegram_id)}, {"wallet.balance": 1})
        if not user:
            return 0
        return int(user.get("wallet", {}).get("balance", 0) or 0)

    def list_transactions(self, telegram_id: int, limit: int | None = 10) -> list[dict]:
        query = self.transactions.find(
            {"telegram_id": int(telegram_id)},
            {"_id": 0},
        ).sort("created_at", -1)
        if limit is not None:
            query = query.limit(limit)
        return list(query)

    def apply_transaction(
        self,
        telegram_id: int,
        store_code: str,
        transaction_type: str,
        source: str,
        amount: int,
        description: str,
        transaction_id: str | None = None,
        admin_telegram_id: int | None = None,
        extra_fields: dict | None = None,
        session=None,
    ) -> tuple[dict, bool]:
        telegram_id = int(telegram_id)
        amount = int(amount)
        if amount <= 0:
            raise ValueError("amount must be positive")
        if transaction_type not in {"credit", "debit"}:
            raise ValueError("transaction_type must be credit or debit")

        transaction_id = transaction_id or manual_transaction_id(source, telegram_id)
        existing = self.transactions.find_one({"transaction_id": transaction_id}, {"_id": 0}, session=session)
        if existing:
            return existing, False

        delta = amount if transaction_type == "credit" else -amount
        now = utc_now()
        query = {
            "telegram_id": telegram_id,
            "wallet.applied_transaction_ids": {"$ne": transaction_id},
        }
        if transaction_type == "debit":
            query["wallet.balance"] = {"$gte": amount}

        updated = self.users.find_one_and_update(
            query,
            {
                "$inc": {"wallet.balance": delta},
                "$set": {"updated_at": now},
                "$addToSet": {"wallet.applied_transaction_ids": transaction_id},
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )

        if not updated:
            if self.transactions.find_one({"transaction_id": transaction_id}, {"_id": 1}, session=session):
                return self.transactions.find_one({"transaction_id": transaction_id}, {"_id": 0}, session=session), False
            raise ValueError("insufficient balance or user not found")

        balance_after = int(updated.get("wallet", {}).get("balance", 0) or 0)
        balance_before = balance_after - delta
        jalali_date, jalali_month, tehran_time = transaction_datetime_parts(now)
        transaction = {
            "transaction_id": transaction_id,
            "telegram_id": telegram_id,
            "store_code": str(store_code),
            "type": transaction_type,
            "source": source,
            "amount": amount,
            "description": description,
            "created_at": now,
            "jalali_date": jalali_date,
            "jalali_month": jalali_month,
            "tehran_time": tehran_time,
            "admin_telegram_id": admin_telegram_id,
            "balance_before": balance_before,
            "balance_after": balance_after,
        }
        if extra_fields:
            transaction.update(extra_fields)

        try:
            self.transactions.insert_one(transaction, session=session)
        except DuplicateKeyError:
            self.users.update_one(
                {"telegram_id": telegram_id, "wallet.applied_transaction_ids": transaction_id},
                {
                    "$inc": {"wallet.balance": -delta},
                    "$pull": {"wallet.applied_transaction_ids": transaction_id},
                    "$set": {"updated_at": utc_now()},
                },
                session=session,
            )
            return self.transactions.find_one({"transaction_id": transaction_id}, {"_id": 0}, session=session), False

        transaction.pop("_id", None)
        return transaction, True
