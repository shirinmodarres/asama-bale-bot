from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bot.config import load_mongo_config
from bot.services.commission_service import BASIS_SALES_AMOUNT, CommissionService
from bot.services.user_service import UserService
from bot.services.wallet_service import WalletService
from bot.utils.mongo import get_database


RULES = {
    "1405/05": [
        {"min": 0, "max": None, "rate": 4},
    ],
    "1405/06": [
        {"min": 0, "max": None, "rate": 2},
        {"min": 5_000_000_000, "max": None, "rate": 4},
    ],
}


def _normalized_tiers(tiers: list[dict]) -> list[dict]:
    return sorted(
        [
            {
                "min": int(tier.get("min", 0) or 0),
                "max": tier.get("max"),
                "rate": float(tier.get("rate", 0) or 0),
            }
            for tier in tiers
        ],
        key=lambda tier: tier["min"],
    )


def _same_rule(existing: dict | None, tiers: list[dict]) -> bool:
    if not existing:
        return False
    return (
        existing.get("basis") == BASIS_SALES_AMOUNT
        and existing.get("calculation_type") == "threshold_full_amount"
        and _normalized_tiers(existing.get("tiers", [])) == _normalized_tiers(tiers)
    )


def seed_commission_rules() -> dict:
    config = load_mongo_config()
    db = get_database()
    wallet_service = WalletService(db)
    user_service = UserService(db, wallet_service=wallet_service)
    commission_service = CommissionService(db, wallet_service=wallet_service, user_service=user_service)

    inserted = 0
    unchanged = 0
    deactivated = 0
    months: list[str] = []

    for month, tiers in RULES.items():
        active = db["commission_rules"].find_one({"month": month, "active": True}, sort=[("version", -1)])
        if _same_rule(active, tiers):
            unchanged += 1
        else:
            if active:
                deactivated += 1
            commission_service.create_rule(
                month=month,
                basis=BASIS_SALES_AMOUNT,
                tiers=tiers,
                admin_telegram_id=None,
            )
            inserted += 1
        months.append(month)

    return {
        "app_env": config.app_env,
        "db_name": config.mongo_db_name,
        "months": ", ".join(months),
        "inserted": inserted,
        "unchanged": unchanged,
        "deactivated": deactivated,
    }


def main() -> None:
    result = seed_commission_rules()
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db_name']}")
    print(f"months: {result['months']}")
    print(f"inserted: {result['inserted']}")
    print(f"unchanged: {result['unchanged']}")
    print(f"deactivated: {result['deactivated']}")


if __name__ == "__main__":
    main()
