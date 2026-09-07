from argparse import ArgumentParser
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


def _collect_targets(db, requested_month: str | None, requested_store: str | None) -> set[tuple[str, str]]:
    targets: set[tuple[str, str]] = set()

    order_filter = {"units.validation_status": "approved"}
    if requested_store:
        order_filter["store_code"] = str(requested_store)
    for order in db["orders"].find(order_filter, {"_id": 0}):
        store_code = str(order.get("store_code", ""))
        if not store_code:
            continue
        for unit in order.get("units", []):
            if unit.get("validation_status") != "approved":
                continue
            decision_at = unit.get("validation_decision_at") or order.get("updated_at") or order.get("created_at")
            if not decision_at:
                continue
            month = month_from_datetime(decision_at)
            if requested_month and month != requested_month:
                continue
            targets.add((store_code, month))

    return_filter = {"status": "approved"}
    if requested_store:
        return_filter["store_code"] = str(requested_store)
    for product_return in db["product_returns"].find(return_filter, {"_id": 0}):
        store_code = str(product_return.get("store_code", ""))
        if not store_code:
            continue
        month = product_return.get("sale_month")
        if not month:
            month = month_from_datetime(product_return.get("sold_at") or product_return.get("created_at"))
        if requested_month and month != requested_month:
            continue
        targets.add((store_code, month))

    return targets


def recalculate_commission_wallet(month: str | None, store_code: str | None, apply: bool) -> dict:
    config = load_mongo_config()
    db = get_database()
    wallet_service = WalletService(db)
    user_service = UserService(db, wallet_service=wallet_service)
    commission_service = CommissionService(db, wallet_service=wallet_service, user_service=user_service)

    rows = []
    for target_store_code, target_month in sorted(_collect_targets(db, month, store_code)):
        before = db["store_monthly_performance"].find_one(
            {"store_code": str(target_store_code), "month": target_month},
            {"_id": 0, "wallet_commission_posted": 1},
        ) or {}
        previous_posted = int(before.get("wallet_commission_posted", 0) or 0)
        performance = commission_service.recalculate_store_month(
            target_store_code,
            target_month,
            post_delta=apply,
            event_id="manual-commission-sync",
        )
        if not performance:
            rows.append(
                {
                    "store_code": target_store_code,
                    "month": target_month,
                    "status": "skipped",
                }
            )
            continue
        entitlement = int(performance.get("commission_entitlement", 0) or 0)
        delta = entitlement - previous_posted
        rows.append(
            {
                "store_code": target_store_code,
                "month": target_month,
                "status": "applied" if apply else "dry-run",
                "net_sales_amount": int(performance.get("net_sales_amount", 0) or 0),
                "commission_rate": performance.get("commission_rate"),
                "previous_posted": previous_posted,
                "entitlement": entitlement,
                "delta": delta,
                "wallet_balance": performance.get("wallet_balance"),
            }
        )

    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "apply": apply,
        "rows": rows,
    }


def main() -> None:
    parser = ArgumentParser(description="Recalculate monthly commission and optionally sync wallet deltas.")
    parser.add_argument("--month", help="Jalali month, for example 1405/06")
    parser.add_argument("--store-code", help="Optional store code")
    parser.add_argument("--apply", action="store_true", help="Post wallet delta transactions")
    args = parser.parse_args()

    result = recalculate_commission_wallet(args.month, args.store_code, args.apply)
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"mode: {'APPLY' if result['apply'] else 'DRY-RUN'}")
    if not result["rows"]:
        print("no targets")
        return
    for row in result["rows"]:
        if row["status"] == "skipped":
            print(f"{row['store_code']} {row['month']} skipped")
            continue
        print(
            f"{row['store_code']} {row['month']} "
            f"rate={row['commission_rate']} "
            f"net_sales={row['net_sales_amount']} "
            f"previous_posted={row['previous_posted']} "
            f"entitlement={row['entitlement']} "
            f"delta={row['delta']} "
            f"wallet_balance={row['wallet_balance']}"
        )


if __name__ == "__main__":
    main()
