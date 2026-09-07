from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pymongo import MongoClient

from bot.config import load_mongo_config
from bot.services.commission_service import (
    BASIS_SALES_AMOUNT,
    CALCULATION_THRESHOLD_FULL_AMOUNT,
    CommissionService,
    utc_now,
)
from bot.services.order_service import OrderService
from bot.services.return_service import ProductReturnError, ProductReturnService
from bot.services.user_service import UserService
from bot.services.wallet_service import WalletService
from bot.utils.mongo import get_mongo_client


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected={expected!r} actual={actual!r}")


def make_draft(quantity: int = 1, price: int = 1000) -> dict:
    units = [
        {
            "index": idx,
            "tracking_code": {"type": "text", "value": f"900{idx}", "file_id": None},
            "factor_image": {"type": "photo", "value": None, "file_id": f"file-{idx}"},
        }
        for idx in range(1, quantity + 1)
    ]
    return {
        "store_code": "1",
        "store_name": "تست",
        "seller_telegram_id": 111,
        "seller_name": "فروشنده تست",
        "seller_phone": "09120000000",
        "expert_telegram_id": 222,
        "expert_name": "کارشناس تست",
        "category_key": "test",
        "category_name": "تست",
        "product_key": "P1",
        "product_code": "P1",
        "product_name": "کالای تست",
        "product_model": "M1",
        "product_price": price,
        "quantity": quantity,
        "units": units,
    }


def validate() -> dict[str, str | int]:
    config = load_mongo_config()
    client: MongoClient = get_mongo_client()
    db_name = f"{config.mongo_db_name}_commission_return_validation"
    client.drop_database(db_name)
    db = client[db_name]

    try:
        db["users"].insert_one(
            {
                "telegram_id": 111,
                "role": "seller",
                "store_code": "1",
                "status": "active",
                "full_name": "فروشنده تست",
                "wallet": {"balance": 0, "transactions": [], "applied_transaction_ids": []},
            }
        )
        db["commission_rules"].insert_one(
            {
                "month": "1405/06",
                "version": 1,
                "basis": BASIS_SALES_AMOUNT,
                "calculation_type": CALCULATION_THRESHOLD_FULL_AMOUNT,
                "tiers": [
                    {"min": 0, "max": 999, "rate": 0},
                    {"min": 1000, "max": 1999, "rate": 2},
                    {"min": 2000, "max": None, "rate": 4},
                ],
                "active": True,
                "created_at": utc_now(),
            }
        )

        wallet_service = WalletService(db)
        user_service = UserService(db, wallet_service=wallet_service)
        commission_service = CommissionService(db, wallet_service=wallet_service, user_service=user_service)
        order_service = OrderService(db)
        return_service = ProductReturnService(db, commission_service=commission_service)

        order = order_service.create_order(make_draft(quantity=2, price=1000))
        order = order_service.approve_unit_validation(order["id"], 1)
        unit_1 = next(unit for unit in order["units"] if unit["index"] == 1)
        order_service.register_sold_tracking_code(order["id"], 1)
        performance = commission_service.recalculate_for_sale(order, unit_1)
        assert_equal(performance["commission_entitlement"], 20, "first tier entitlement")

        order = order_service.approve_unit_validation(order["id"], 2)
        unit_2 = next(unit for unit in order["units"] if unit["index"] == 2)
        order_service.register_sold_tracking_code(order["id"], 2)
        performance = commission_service.recalculate_for_sale(order, unit_2)
        assert_equal(performance["commission_entitlement"], 80, "threshold crossing uses full amount")
        assert_equal(wallet_service.get_balance(111), 80, "wallet posts only delta")
        crossed_message = commission_service.build_realtime_message(performance)
        forbidden_money_unit = "\u062a\u0648\u0645\u0627\u0646"
        if forbidden_money_unit in crossed_message or "ریال" not in crossed_message or "زدی به هدف" not in crossed_message:
            raise AssertionError("threshold crossing message should be rial-based and congratulatory")

        duplicate = order_service.approve_unit_validation(order["id"], 2)
        assert_equal(duplicate, None, "duplicate approval is blocked")
        performance = commission_service.recalculate_store_month("1", "1405/06")
        repeated_message = commission_service.build_realtime_message(performance)
        if "زدی به هدف" in repeated_message:
            raise AssertionError("threshold crossing message should not repeat without a crossing event")
        assert_equal(wallet_service.get_balance(111), 80, "duplicate recalculation does not double post")

        seller = user_service.get_user(111)
        rejected_draft = {
            "tracking_code": "9001",
            "return_type": "defective",
            "quantity": 1,
            "invoice_image_path": "data/uploads/returns/test.jpg",
        }
        rejected_return = return_service.create_return_request(seller, rejected_draft)
        return_service.reject_return(rejected_return["return_id"], 222, "رد تست")
        tracking = db["product_tracking_codes"].find_one({"tracking_code": "9001"}, {"_id": 0})
        assert_equal(tracking["status"], "sold", "rejected return does not change tracking")

        approved_draft = {
            "tracking_code": "9001",
            "return_type": "resellable",
            "quantity": 1,
            "invoice_image_path": "data/uploads/returns/test.jpg",
        }
        approved_return = return_service.create_return_request(seller, approved_draft)
        approved_return = return_service.approve_return(approved_return["return_id"], 222)
        try:
            return_service.create_return_request(seller, approved_draft)
        except ProductReturnError:
            pass
        else:
            raise AssertionError("duplicate approved return should be blocked")
        tracking = db["product_tracking_codes"].find_one({"tracking_code": "9001"}, {"_id": 0})
        assert_equal(tracking["status"], "returned_resellable", "resellable return tracking status")
        assert_equal(order_service.tracking_code_exists("9001"), False, "resellable code can be sold again")
        performance = approved_return.get("commission_performance")
        assert_equal(performance["commission_entitlement"], 20, "return drops threshold")
        assert_equal(wallet_service.get_balance(111), 20, "return posts negative delta")
        decreased_message = commission_service.build_realtime_message(performance)
        if "از پورسانت این ماهت کم شد" not in decreased_message:
            raise AssertionError("approved return should show commission decrease message")

        order_2 = order_service.create_order(make_draft(quantity=1, price=1000))
        order_2["units"][0]["tracking_code"]["value"] = "9001"
        db["orders"].update_one({"id": order_2["id"]}, {"$set": {"units": order_2["units"]}})
        order_2 = order_service.approve_unit_validation(order_2["id"], 1)
        order_service.register_sold_tracking_code(order_2["id"], 1)
        tracking = db["product_tracking_codes"].find_one({"tracking_code": "9001"}, {"_id": 0})
        assert_equal(tracking["status"], "sold", "resellable code becomes sold after new approval")
        assert_equal(order_service.tracking_code_exists("9001"), True, "sold code is duplicate")

        defective_draft = {
            "tracking_code": "9002",
            "return_type": "defective",
            "quantity": 1,
            "invoice_image_path": "data/uploads/returns/test.jpg",
        }
        defective_return = return_service.create_return_request(seller, defective_draft)
        return_service.approve_return(defective_return["return_id"], 222)
        tracking = db["product_tracking_codes"].find_one({"tracking_code": "9002"}, {"_id": 0})
        assert_equal(tracking["status"], "returned_defective", "defective return tracking status")
        assert_equal(order_service.tracking_code_exists("9002"), True, "defective code cannot be sold again")

        return {"db_name": db_name, "status": "ok"}
    finally:
        client.drop_database(db_name)


def main() -> None:
    result = validate()
    print(f"DB: {result['db_name']}")
    print(f"status: {result['status']}")


if __name__ == "__main__":
    main()
