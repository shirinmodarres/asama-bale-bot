from datetime import datetime

from bot.utils.mongo import get_database
from data.static_data import BOT_ACTIVE, CATEGORIES, SALES_EXPERTS, STORES

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"


class AdminService:
    def __init__(self, db=None):
        self.db = db or get_database()

        self.settings = self.db["admin_settings"]
        self.action_requests = self.db["admin_action_requests"]

        # ایجاد تنظیمات اولیه در صورت نبودن
        if self.settings.find_one({"_id": "main"}) is None:
            self.settings.insert_one({
                "_id": "main",
                "bot_active": BOT_ACTIVE,
            })

    # =========================
    # Bot Status
    # =========================

    def bot_active(self) -> bool:
        data = self.settings.find_one({"_id": "main"})
        if not data:
            return BOT_ACTIVE
        return data.get("bot_active", BOT_ACTIVE)

    def set_bot_active(self, active: bool) -> bool:
        self.settings.update_one(
            {"_id": "main"},
            {"$set": {"bot_active": bool(active)}},
            upsert=True,
        )
        return bool(active)

    # =========================
    # Stores
    # =========================

    def list_stores(self) -> list[dict]:
        stores = []

        for code in sorted(STORES.keys(), key=lambda item: int(item)):
            store = self.get_store(code)
            if store:
                stores.append(store)

        return stores

    def get_store(self, code: str) -> dict | None:
        code = str(code).strip()

        store = STORES.get(code)

        if not store:
            return None

        status = self.db["admin_store_status"].find_one({
            "_id": code
        })

        active = (
            status.get("active")
            if status is not None
            else store.get("active", True)
        )

        result = dict(store)
        result["active"] = active

        return result

    def set_store_active(self, code: str, active: bool) -> bool:
        code = str(code).strip()

        if code not in STORES:
            return False

        self.db["admin_store_status"].update_one(
            {"_id": code},
            {
                "$set": {
                    "active": bool(active),
                    "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
                }
            },
            upsert=True,
        )

        return True

    # =========================
    # Experts
    # =========================

    def list_experts(self) -> list[dict]:
        experts = []

        for key in sorted(SALES_EXPERTS.keys()):
            expert = self.get_expert(key)
            if expert:
                experts.append(expert)

        return experts

    def get_expert(self, expert_key: str) -> dict | None:
        expert = SALES_EXPERTS.get(expert_key)

        if not expert:
            return None

        status = self.db["admin_expert_status"].find_one({
            "_id": expert_key
        })

        active = (
            status.get("active")
            if status is not None
            else expert.get("active", True)
        )

        result = dict(expert)
        result["expert_key"] = expert_key
        result["active"] = active

        return result

    def set_expert_active(self, expert_key: str, active: bool) -> bool:
        if expert_key not in SALES_EXPERTS:
            return False

        self.db["admin_expert_status"].update_one(
            {"_id": expert_key},
            {
                "$set": {
                    "active": bool(active),
                    "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
                }
            },
            upsert=True,
        )

        return True

    # =========================
    # Products
    # =========================

    def list_products(self, active: bool | None = None) -> list[dict]:
        products = []

        for category_key, category in CATEGORIES.items():
            for product_key in category["products"].keys():

                item = self.get_product(
                    category_key,
                    product_key,
                )

                if item is None:
                    continue

                if active is None or item["active"] == active:
                    products.append(item)

        return products

    def get_product(
        self,
        category_key: str,
        product_key: str,
    ) -> dict | None:

        category = CATEGORIES.get(category_key)

        if not category:
            return None

        product = category["products"].get(product_key)

        if not product:
            return None

        status_id = f"{category_key}:{product_key}"

        status = self.db["admin_product_status"].find_one({
            "_id": status_id
        })

        active = (
            status.get("active")
            if status is not None
            else product.get("active", True)
        )

        result = dict(product)

        result["category_key"] = category_key
        result["category_name"] = category["name"]
        result["product_key"] = product_key
        result["active"] = active

        return result

    def set_product_active(
        self,
        category_key: str,
        product_key: str,
        active: bool,
    ) -> bool:

        category = CATEGORIES.get(category_key)

        if not category:
            return False

        if product_key not in category["products"]:
            return False

        status_id = f"{category_key}:{product_key}"

        self.db["admin_product_status"].update_one(
            {"_id": status_id},
            {
                "$set": {
                    "category_key": category_key,
                    "product_key": product_key,
                    "active": bool(active),
                    "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
                }
            },
            upsert=True,
        )

        return True

    # =========================
    # Admin Action Requests
    # =========================

    def create_admin_action_request(
        self,
        title: str,
        action_type: str,
        payload: dict,
        initiated_by: int,
    ) -> dict:

        last_request = self.action_requests.find_one(
            {},
            sort=[("id", -1)],
        )

        next_id = (
            int(last_request["id"]) + 1
            if last_request
            else 1
        )

        now = datetime.utcnow().isoformat(timespec="seconds")

        request = {
            "id": next_id,
            "title": title,
            "action_type": action_type,
            "payload": payload,
            "status": PENDING,
            "initiated_by": initiated_by,
            "approver_id": None,
            "reject_reason": "",
            "created_at": now,
            "updated_at": now,
        }

        self.action_requests.insert_one(request)

        return request

    def list_admin_action_requests(
        self,
        status: str | None = None,
    ) -> list[dict]:

        query = {}

        if status is not None:
            query["status"] = status

        return list(
            self.action_requests.find(
                query,
                {"_id": 0},
            ).sort("id", 1)
        )

    def get_admin_action_request(
        self,
        request_id: int,
    ) -> dict | None:

        return self.action_requests.find_one(
            {"id": int(request_id)},
            {"_id": 0},
        )

    def _update_admin_action_request(
        self,
        request_id: int,
        **changes,
    ) -> dict | None:

        changes["updated_at"] = datetime.utcnow().isoformat(
            timespec="seconds"
        )

        result = self.action_requests.update_one(
            {"id": int(request_id)},
            {"$set": changes},
        )

        if result.matched_count == 0:
            return None

        return self.get_admin_action_request(request_id)

    def approve_admin_action_request(
        self,
        request_id: int,
        approver_id: int,
    ) -> dict | None:

        request = self._update_admin_action_request(
            request_id,
            status=APPROVED,
            approver_id=approver_id,
        )

        if not request:
            return None

        self._apply_admin_action_request(request)

        return request

    def reject_admin_action_request(
        self,
        request_id: int,
        approver_id: int,
        reason: str,
    ) -> dict | None:

        return self._update_admin_action_request(
            request_id,
            status=REJECTED,
            approver_id=approver_id,
            reject_reason=reason,
        )

    # =========================
    # Apply Approved Action
    # =========================

    def _apply_admin_action_request(
        self,
        request: dict,
    ) -> None:

        action_type = request.get("action_type")
        payload = request.get("payload", {})

        if action_type == "product_toggle":

            self.set_product_active(
                payload.get("category_key", ""),
                payload.get("product_key", ""),
                payload.get("active", True),
            )

        elif action_type == "store_toggle":

            self.set_store_active(
                payload.get("store_code", ""),
                payload.get("active", True),
            )

        elif action_type == "expert_toggle":

            self.set_expert_active(
                payload.get("expert_key", ""),
                payload.get("active", True),
            )

        elif action_type == "bot_toggle":

            self.set_bot_active(
                payload.get("active", True)
            )
