from datetime import datetime, timezone

from bot.data.statuses import (
    ORDER_APPROVED_BY_EXPERT,
    ORDER_PARTIALLY_APPROVED_BY_EXPERT,
    ORDER_PENDING_EXPERT_VALIDATION,
    ORDER_REJECTED_BY_EXPERT,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class OrderService:
    def __init__(self, db):
        self.collection = db["orders"]

    def create_order(self, draft: dict) -> dict:
        last_order = self.collection.find_one(
            {},
            sort=[("_sequence", -1)],
        )

        next_id = (
            int(last_order["_sequence"]) + 1
            if last_order
            else 1
        )

        now = utc_now()
        units = [
            self._normalize_unit(draft, unit)
            for unit in draft["units"]
        ]

        order = {
            "_sequence": next_id,
            "id": f"ORD-{next_id:06d}",
            "store_code": draft["store_code"],
            "store_name": draft["store_name"],
            "seller_telegram_id": draft["seller_telegram_id"],
            "seller_name": draft["seller_name"],
            "seller_phone": draft["seller_phone"],
            "expert_telegram_id": draft["expert_telegram_id"],
            "expert_name": draft["expert_name"],
            "category_key": draft["category_key"],
            "category_name": draft["category_name"],
            "product_key": draft["product_key"],
            "product_name": draft["product_name"],
            "product_model": draft["product_model"],
            "product_price": draft.get("product_price", 0),
            "quantity": draft["quantity"],
            "units": units,
            "status": ORDER_PENDING_EXPERT_VALIDATION,
            "rejection_reason_key": None,
            "rejection_reason_text": None,
            "created_at": now,
            "updated_at": now,
        }

        self.collection.insert_one(order)

        order.pop("_id", None)

        return order

    def get_order(self, order_id: str):
        return self.collection.find_one(
            {"id": order_id},
            {"_id": 0, "_sequence": 0},
        )

    def list_orders(self) -> list[dict]:
        return list(
            self.collection.find(
                {},
                {"_id": 0, "_sequence": 0},
            ).sort("_sequence", 1)
        )

    def list_pending_for_stores(
        self,
        store_codes: set[str],
    ) -> list[dict]:

        orders = self.collection.find(
            {
                "store_code": {
                    "$in": list(store_codes),
                },
            },
            {
                "_id": 0,
                "_sequence": 0,
            },
        ).sort("_sequence", 1)

        return [
            order
            for order in orders
            if self.has_pending_units(order)
        ]

    def has_pending_units(
        self,
        order: dict,
    ) -> bool:

        return (
            order["status"]
            == ORDER_PENDING_EXPERT_VALIDATION
            and any(
                unit.get(
                    "validation_status",
                    "pending",
                )
                == "pending"
                for unit in order.get(
                    "units",
                    [],
                )
            )
        )

    def approve_unit_validation(
        self,
        order_id: str,
        unit_index: int,
    ) -> dict | None:

        return self._update_unit(
            order_id,
            unit_index,
            validation_status="approved",
            rejection_reason_key=None,
            rejection_reason_text=None,
        )

    def reject_unit_validation(
        self,
        order_id: str,
        unit_index: int,
        reason_key: str,
        reason_text: str,
    ) -> dict | None:

        return self._update_unit(
            order_id,
            unit_index,
            validation_status="rejected",
            rejection_reason_key=reason_key,
            rejection_reason_text=reason_text,
        )

    def _update_unit(
        self,
        order_id: str,
        unit_index: int,
        **changes,
    ):

        order = self.collection.find_one(
            {"id": order_id},
        )

        if not order:
            return None

        units = order.get("units", [])

        for unit in units:
            if int(unit["index"]) == int(unit_index):

                unit.update(changes)
                unit["validation_decision_at"] = utc_now()

                order["status"] = self._calculate_order_status(
                    order
                )

                order["updated_at"] = utc_now()

                self.collection.update_one(
                    {"id": order_id},
                    {
                        "$set": {
                            "units": units,
                            "status": order["status"],
                            "updated_at": order["updated_at"],
                        }
                    },
                )

                return self.get_order(order_id)

        return None

    def _normalize_unit(
        self,
        draft: dict,
        unit: dict,
    ) -> dict:

        normalized = dict(unit)
        normalized.update(
            {
                "store_code": draft["store_code"],
                "store_name": draft["store_name"],
                "seller_telegram_id": draft["seller_telegram_id"],
                "seller_name": draft["seller_name"],
                "seller_phone": draft["seller_phone"],
                "expert_telegram_id": draft["expert_telegram_id"],
                "expert_name": draft["expert_name"],
                "category_key": draft["category_key"],
                "category_name": draft["category_name"],
                "product_key": draft["product_key"],
                "product_name": draft["product_name"],
                "product_model": draft["product_model"],
                "product_price": draft.get("product_price", 0),
                "validation_decision_at": unit.get("validation_decision_at", ""),
            }
        )
        normalized.setdefault("validation_status", "pending")
        normalized.setdefault("rejection_reason_key", None)
        normalized.setdefault("rejection_reason_text", None)
        return normalized

    def _calculate_order_status(
        self,
        order: dict,
    ) -> str:

        statuses = [
            unit.get(
                "validation_status",
                "pending",
            )
            for unit in order.get(
                "units",
                [],
            )
        ]

        if not statuses or "pending" in statuses:
            return ORDER_PENDING_EXPERT_VALIDATION

        if all(
            status == "approved"
            for status in statuses
        ):
            return ORDER_APPROVED_BY_EXPERT

        if all(
            status == "rejected"
            for status in statuses
        ):
            return ORDER_REJECTED_BY_EXPERT

        return ORDER_PARTIALLY_APPROVED_BY_EXPERT
