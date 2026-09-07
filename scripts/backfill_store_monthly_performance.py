from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bot.config import load_mongo_config
from bot.services.commission_service import CommissionService, month_from_datetime
from bot.services.user_service import UserService
from bot.services.wallet_service import WalletService
from bot.utils.mongo import get_database


def backfill_store_monthly_performance() -> dict[str, int | str]:
    config = load_mongo_config()
    db = get_database()
    wallet_service = WalletService(db)
    user_service = UserService(db, wallet_service=wallet_service)
    commission_service = CommissionService(db, wallet_service=wallet_service, user_service=user_service)

    targets: set[tuple[str, str]] = set()
    for order in db["orders"].find({"units.validation_status": "approved"}, {"_id": 0}):
        store_code = str(order.get("store_code", ""))
        if not store_code:
            continue
        for unit in order.get("units", []):
            if unit.get("validation_status") != "approved":
                continue
            decision_at = unit.get("validation_decision_at") or order.get("updated_at") or order.get("created_at")
            if decision_at:
                targets.add((store_code, month_from_datetime(decision_at)))

    for product_return in db["product_returns"].find({"status": "approved"}, {"_id": 0}):
        store_code = str(product_return.get("store_code", ""))
        if not store_code:
            continue
        month = product_return.get("sale_month")
        if not month:
            month = month_from_datetime(product_return.get("sold_at") or product_return.get("created_at"))
        targets.add((store_code, month))

    rebuilt = 0
    skipped = 0
    for store_code, month in sorted(targets):
        performance = commission_service.recalculate_store_month(
            store_code,
            month,
            post_delta=False,
            mark_posted_to_entitlement=True,
        )
        if performance:
            rebuilt += 1
        else:
            skipped += 1

    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "rebuilt": rebuilt,
        "skipped": skipped,
    }


def main() -> None:
    result = backfill_store_monthly_performance()
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"rebuilt: {result['rebuilt']}")
    print(f"skipped: {result['skipped']}")


if __name__ == "__main__":
    main()
