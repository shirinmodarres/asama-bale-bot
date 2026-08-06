import argparse
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from bot.config import load_mongo_config
from bot.utils.mongo import get_database
from data.static_data import CATEGORIES


def _product_documents() -> list[dict]:
    documents = []
    for category_key, category in CATEGORIES.items():
        for product_key, product in category.get("products", {}).items():
            product_code = str(product.get("code") or product_key)
            documents.append(
                {
                    "_id": product_code,
                    "product_key": str(product_key),
                    "product_code": product_code,
                    "product_name": product.get("name", ""),
                    "product_model": product.get("model", ""),
                    "category_key": str(category_key),
                    "category_name": category.get("name", ""),
                    "brand_key": product.get("brand_key", "naniwa"),
                    "brand_name": product.get("brand_name", "نانیوا"),
                    "price": int(product.get("price") or 0),
                    "is_active": bool(product.get("active", True)),
                }
            )
    return documents


def seed_products(replace: bool = False) -> dict[str, int | str]:
    if load_dotenv:
        load_dotenv()

    mongo_config = load_mongo_config()
    db = get_database()
    products = db["products"]
    documents = _product_documents()

    if replace:
        products.delete_many({})

    upserted = 0
    for document in documents:
        is_active = document.pop("is_active")
        result = products.update_one(
            {"_id": document["_id"]},
            {
                "$set": document,
                "$setOnInsert": {
                    "is_active": is_active,
                    "active": is_active,
                },
            },
            upsert=True,
        )
        if result.upserted_id is not None or result.modified_count:
            upserted += 1

    products.create_index("product_key")
    products.create_index("product_code")
    products.create_index("category_key")
    products.create_index("is_active")

    return {
        "app_env": mongo_config.app_env,
        "db": mongo_config.mongo_db_name,
        "products_total": products.count_documents({}),
        "active_products": products.count_documents({"is_active": True}),
        "seeded_or_updated": upserted,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed products into MongoDB.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing products before seeding.",
    )
    args = parser.parse_args()

    result = seed_products(replace=args.replace)
    print(f"APP_ENV: {result['app_env']}")
    print(f"DB: {result['db']}")
    print(f"products_total: {result['products_total']}")
    print(f"active_products: {result['active_products']}")
    print(f"seeded_or_updated: {result['seeded_or_updated']}")


if __name__ == "__main__":
    main()
