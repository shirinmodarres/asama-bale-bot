from datetime import datetime, timezone

from bot.data.statuses import (
    APPROVED_BY_EXPERT,
    APPROVED_BY_MANAGER,
    PENDING_EXPERT,
    PENDING_MANAGER,
    PENDING_SELLER_CONFIRMATION,
    REJECTED_BY_EXPERT,
    REJECTED_BY_MANAGER,
)
from data.static_data import STORES


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RequestService:
    def __init__(self, db):
        self.collection = db["requests"]

    def create_request(
        self,
        seller: dict,
        expert: dict,
        items: list[dict],
    ) -> dict:

        last_request = self.collection.find_one(
            {},
            sort=[("id", -1)],
        )

        next_id = (
            int(last_request["id"]) + 1
            if last_request
            else 1
        )

        now = utc_now()

        request = {
            "id": next_id,
            "store_code": seller["store_code"],
            "store_name": STORES.get(str(seller["store_code"]), {}).get("name", ""),
            "seller_telegram_id": seller["telegram_id"],
            "seller_full_name": seller["full_name"],
            "seller_phone": seller["phone"],
            "expert_telegram_id": expert["telegram_id"],
            "expert_name": expert["full_name"],
            "items": items,
            "status": PENDING_EXPERT,
            "expert_reject_reason": "",
            "manager_reject_reason": "",
            "expert_decision_at": "",
            "manager_decision_at": "",
            "created_at": now,
            "updated_at": now,
        }

        self.collection.insert_one(request)

        request.pop("_id", None)

        return request

    def get_request(self, request_id: int):
        request = self.collection.find_one(
            {"id": int(request_id)},
            {"_id": 0},
        )

        return request

    def list_requests(self) -> list[dict]:
        return list(
            self.collection.find(
                {},
                {"_id": 0},
            ).sort("id", 1)
        )

    def list_requests_for_seller(
        self,
        telegram_id: int,
    ) -> list[dict]:

        return list(
            self.collection.find(
                {
                    "seller_telegram_id": int(telegram_id),
                },
                {"_id": 0},
            ).sort("id", 1)
        )

    def list_requests_for_stores(
        self,
        store_codes: set[str],
    ) -> list[dict]:

        return list(
            self.collection.find(
                {
                    "store_code": {
                        "$in": list(store_codes),
                    },
                },
                {"_id": 0},
            ).sort("id", 1)
        )

    def list_pending_for_stores(
        self,
        store_codes: set[str],
    ) -> list[dict]:

        return list(
            self.collection.find(
                {
                    "store_code": {
                        "$in": list(store_codes),
                    },
                    "status": PENDING_EXPERT,
                },
                {"_id": 0},
            ).sort("id", 1)
        )

    def finalize_request(self, request_id: int):
        return self._update(
            request_id,
            status=APPROVED_BY_EXPERT,
            expert_decision_at=utc_now(),
        )

    approve_by_expert = finalize_request

    def reject_by_expert(
        self,
        request_id: int,
        reason: str,
    ):
        return self._update(
            request_id,
            status=REJECTED_BY_EXPERT,
            expert_reject_reason=reason,
            expert_decision_at=utc_now(),
        )

    def approve_by_manager(
        self,
        request_id: int,
    ):
        return self._update(
            request_id,
            status=APPROVED_BY_MANAGER,
            manager_decision_at=utc_now(),
        )

    def reject_by_manager(
        self,
        request_id: int,
        reason: str,
    ):
        return self._update(
            request_id,
            status=REJECTED_BY_MANAGER,
            manager_reject_reason=reason,
            manager_decision_at=utc_now(),
        )

    def merge_draft_item(
        self,
        items: list[dict],
        new_item: dict,
    ) -> bool:

        for item in items:
            if item["product_key"] == new_item["product_key"]:
                item["carton_quantity"] += new_item[
                    "carton_quantity"
                ]
                return True

        items.append(new_item)
        return False

    def update_draft_item_quantity(
        self,
        items: list[dict],
        index: int,
        quantity: int,
    ) -> bool:

        if index < 0 or index >= len(items):
            return False

        items[index]["carton_quantity"] = quantity

        return True

    def update_request_item_quantity(
        self,
        request_id: int,
        index: int,
        quantity: int,
    ):

        request = self.get_request(request_id)

        if not request:
            return None

        items = request.get("items", [])

        if index < 0 or index >= len(items):
            return None

        items[index]["carton_quantity"] = quantity

        request["updated_at"] = utc_now()

        self.collection.update_one(
            {"id": int(request_id)},
            {
                "$set": {
                    "items": items,
                    "updated_at": request["updated_at"],
                }
            },
        )

        return request

    def propose_item_quantity_change(
        self,
        request_id: int,
        index: int,
        new_quantity: int,
    ):

        request = self.get_request(request_id)

        if not request:
            return None

        items = request.get("items", [])

        if index < 0 or index >= len(items):
            return None

        items[index]["pending_quantity"] = new_quantity
        items[index]["quantity_change_status"] = "pending"

        now = utc_now()

        request["status"] = PENDING_SELLER_CONFIRMATION
        request["updated_at"] = now

        self.collection.update_one(
            {"id": int(request_id)},
            {
                "$set": {
                    "items": items,
                    "status": PENDING_SELLER_CONFIRMATION,
                    "updated_at": now,
                }
            },
        )

        return request

    def confirm_item_quantity_change(
        self,
        request_id: int,
        index: int,
    ):

        request = self.get_request(request_id)

        if not request:
            return None

        items = request.get("items", [])

        if index < 0 or index >= len(items):
            return None

        item = items[index]

        if "pending_quantity" not in item:
            return None

        item["carton_quantity"] = item.pop(
            "pending_quantity"
        )

        item["quantity_change_status"] = "confirmed"

        now = utc_now()

        request["status"] = PENDING_EXPERT
        request["expert_decision_at"] = ""
        request["updated_at"] = now

        self.collection.update_one(
            {"id": int(request_id)},
            {
                "$set": {
                    "items": items,
                    "status": PENDING_EXPERT,
                    "expert_decision_at": "",
                    "updated_at": now,
                }
            },
        )

        return request

    def reject_item_quantity_change(
        self,
        request_id: int,
        index: int,
    ):

        request = self.get_request(request_id)

        if not request:
            return None

        items = request.get("items", [])

        if index < 0 or index >= len(items):
            return None

        item = items[index]

        if "pending_quantity" not in item:
            return None

        item.pop("pending_quantity", None)

        item["quantity_change_status"] = "rejected"

        now = utc_now()

        request["status"] = PENDING_EXPERT
        request["seller_reject_reason"] = (
            "فروشنده پیشنهاد تغییر تعداد را رد کرد."
        )
        request["updated_at"] = now

        self.collection.update_one(
            {"id": int(request_id)},
            {
                "$set": {
                    "items": items,
                    "status": PENDING_EXPERT,
                    "seller_reject_reason": (
                        "فروشنده پیشنهاد تغییر تعداد را رد کرد."
                    ),
                    "updated_at": now,
                }
            },
        )

        return request

    def remove_draft_item(
        self,
        items: list[dict],
        index: int,
    ) -> bool:

        if index < 0 or index >= len(items):
            return False

        items.pop(index)

        return True

    def _update(
        self,
        request_id: int,
        **changes,
    ):

        changes["updated_at"] = utc_now()

        result = self.collection.update_one(
            {"id": int(request_id)},
            {
                "$set": changes,
            },
        )

        if result.matched_count == 0:
            return None

        return self.get_request(request_id)
