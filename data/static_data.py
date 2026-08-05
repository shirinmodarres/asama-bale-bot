"""
Single source of manually maintained MVP data.

Edit Telegram IDs, stores, experts, manager/admin, categories, and products here.
Do not hardcode this data inside handlers.
"""
import os
from copy import deepcopy
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

ORG_CACHE_TTL = timedelta(seconds=60)
_ORG_CACHE = None
_ORG_CACHE_UNTIL = None

ADMINS = [
    {"telegram_id": 700144333, "full_name": "Amir Kamali"}, 
    {"telegram_id": 583160697, "full_name": "Shirin Modarres"},
]

BOT_ACTIVE = True

SALES_MANAGER = {
    "telegram_id": 132500720,
    "full_name": "Sales Manager",
}

SALES_EXPERTS = {
    "expert_1": {
        "telegram_id": 359839746,
        "full_name": "آقای کوهی ",
    },
    "expert_2": {
        "telegram_id": 557925611,
        "full_name": "خانم مدیری",
    },
}

STORES = {
    "1": {"code": "1", "name": "فکوری", "expert_key": "expert_1"},
    "2": {"code": "2", "name": "کرج", "expert_key": "expert_1"},
    "3": {"code": "3", "name": "تبریز", "expert_key": "expert_1"},
    "4": {"code": "4", "name": "فلاحی", "expert_key": "expert_1"},
    "5": {"code": "5", "name": "رشت", "expert_key": "expert_1"},
    "6": {"code": "6", "name": "شهدای انقلاب", "expert_key": "expert_1"},
    "7": {"code": "7", "name": "امامی نسب", "expert_key": "expert_1"},
    "8": {"code": "8", "name": "لویزان", "expert_key": "expert_1"},
    "9": {"code": "9", "name": "فردیس", "expert_key": "expert_1"},
    "10": {"code": "10", "name": "شهید محلاتی", "expert_key": "expert_1"},
    "11": {"code": "11", "name": "مراغه", "expert_key": "expert_1"},
    "12": {"code": "12", "name": "رودهن", "expert_key": "expert_1"},
    "13": {"code": "13", "name": "اردبیل", "expert_key": "expert_1"},
    "14": {"code": "14", "name": "یاسوج", "expert_key": "expert_1"},
    "15": {"code": "15", "name": "اراک", "expert_key": "expert_1"},
    "16": {"code": "16", "name": "شهرکرد", "expert_key": "expert_1"},
    "17": {"code": "17", "name": "زنجان", "expert_key": "expert_1"},
    "18": {"code": "18", "name": "بیرجند", "expert_key": "expert_1"},
    "19": {"code": "19", "name": "اهواز", "expert_key": "expert_1"},
    "20": {"code": "20", "name": "شاهین شهر", "expert_key": "expert_1"},
    "21": {"code": "21", "name": "گرگان", "expert_key": "expert_1"},
    "22": {"code": "22", "name": "سنندج", "expert_key": "expert_1"},
    "23": {"code": "23", "name": "فتح المبین(شیراز)", "expert_key": "expert_1"},
    "24": {"code": "24", "name": "چمران", "expert_key": "expert_2"},
    "25": {"code": "25", "name": "رجایی", "expert_key": "expert_2"},
    "26": {"code": "26", "name": "کرمانشاه مرکزی", "expert_key": "expert_2"},
    "27": {"code": "27", "name": "اصفهان", "expert_key": "expert_2"},
    "28": {"code": "28", "name": "زاهدان", "expert_key": "expert_2"},
    "29": {"code": "29", "name": "ساری", "expert_key": "expert_2"},
    "30": {"code": "30", "name": "سمنان", "expert_key": "expert_2"},
    "31": {"code": "31", "name": "قم", "expert_key": "expert_2"},
    "32": {"code": "32", "name": "بجنورد", "expert_key": "expert_2"},
    "33": {"code": "33", "name": "یزد", "expert_key": "expert_2"},
    "34": {"code": "34", "name": "همدان", "expert_key": "expert_2"},
    "35": {"code": "35", "name": "قزوین", "expert_key": "expert_2"},
    "36": {"code": "36", "name": "ایلام", "expert_key": "expert_2"},
    "37": {"code": "37", "name": "قصر فیروزه", "expert_key": "expert_2"},
    "38": {"code": "38", "name": "دزفول", "expert_key": "expert_2"},
    "39": {"code": "39", "name": "ارومیه", "expert_key": "expert_2"},
    "1382": {"code": "1382", "name": "تست", "expert_key": "expert_1"},
}

CATEGORIES = {
"grinder": {
"name": "آسیاب",
"products": {
"12100235": {"name": "آسیاب و خردکن 800 وات مدل 321-N", "model": "321-N", "code": "12100235", "price": 39556364},
"12100238": {"name": "آسیاب و خردکن 800 وات مدل 322-N", "model": "322-N", "code": "12100238", "price": 45703636},
"12100239": {"name": "آسیاب و خرد کن 350 وات کاسه دار مدل 310-A مشکی", "model": "310-A", "code": "12100239", "price": 45080000},
"12100246": {"name": "آسیاب قهوه 150 وات مدل N95", "model": "N95", "code": "12100246", "price": 23831818},
},
},
"mixer_blender": {
"name": "مخلوط کن",
"products": {
"12100249": {"name": "مخلوط کن / بلندر مدل 395-N", "model": "395-N", "code": "12100249", "price": 40180000},
},
},
"mixer": {
"name": "همزن",
"products": {
"12100255": {"name": "غذاساز چند کاره روند و مدل N400", "model": "N400", "code": "12100255", "price": 44545455},
"12100253": {"name": "همزن مدل 645", "model": "645", "code": "12100253", "price": 28224000},
"12100252": {"name": "همزن دستی مدل 644", "model": "644", "code": "12100252", "price": 31181818},
"12100251": {"name": "همزن چهار تیغه مدل 656", "model": "656", "code": "12100251", "price": 31894545},
},
},
"hand_blender": {
"name": "گوشت کوب",
"products": {
"12100270": {"name": "گوشت کوب برقی 200 وات تک کاره مدل 510-NHB", "model": "510-NHB", "code": "12100270", "price": 28776364},
"12100269": {"name": "گوشت کوب برقی دو تیغه مدل 520", "model": "520", "code": "12100269", "price": 56572727},
},
},
"juicer": {
"name": "آبمیوه گیری",
"products": {
"MJ176": {"name": "آبمیوه گیری سه کاره مدل MJ176", "model": "MJ176", "code": "12400366", "price": 51227273},
"178-N": {"name": "آبمیوه گیری چهار کاره مدل 178-N", "model": "178-N", "code": "12400363", "price": 130607273},
"NJ22": {"name": "آب مرکبات گیر مدل NJ22", "model": "NJ22", "code": "12400697", "price": 23520000},
},
},
"vacuum_cleaner": {
"name": "جاروبرقی",
"products": {
"NCV-9870": {"name": "جاروبرقی 2200 وات مدل NCV-9870", "model": "NCV-9870", "code": "12200319", "price": 220500000},
},
},
"meat_grinder": {
"name": "چرخ گوشت",
"products": {
"MKG50": {"name": "چرخ گوشت 1500 وات مدل MKG50", "model": "MKG50", "code": "12100265", "price": 115640000},
"MKG70": {"name": "چرخ گوشت 2000 وات مدل MKG70", "model": "MKG70", "code": "12100268", "price": 155909091},
"MKG60": {"name": "چرخ گوشت 2000 وات مدل MKG60", "model": "MKG60", "code": "12100267", "price": 158136364},
},
},
"fan": {
"name": "پنکه",
"products": {
"NSF4035": {"name": "پنکه پایه بلند 55 وات مدل NSF4035", "model": "NSF4035", "code": "12500384", "price": 72831818},
},
},
"tea_maker": {
"name": "چای ساز",
"products": {
"NTM4110": {"name": "چای ساز مدل NTM4110", "model": "NTM4110", "code": "12400356", "price": 79290909},
"NTM4200": {"name": "چای ساز مدل NTM4200", "model": "NTM4200", "code": "12400354", "price": 80181818},
"NTM5000": {"name": "چای ساز مدل NTM5000", "model": "NTM5000", "code": "12400357", "price": 81830000},
},
},
}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    return int(value)


def _env_admins() -> list[dict]:
    raw_ids = os.getenv("LOCAL_ADMIN_IDS", "583160697").strip()
    return [
        {"telegram_id": int(item.strip()), "full_name": f"Local Admin {item.strip()}"}
        for item in raw_ids.split(",")
        if item.strip()
    ]


LOCAL_ADMINS = _env_admins()

LOCAL_SALES_MANAGER = {
    "telegram_id": _env_int("LOCAL_SALES_MANAGER_ID", 132500720),
    "full_name": "Local Sales Manager",
}

LOCAL_SALES_EXPERTS = {
    "local_expert": {
        "telegram_id": _env_int("LOCAL_EXPERT_ID", 700144333),
        "full_name": "کارشناس تست لوکال",
    },
}

LOCAL_STORES = {
    "1382": {"code": "1382", "name": "فروشگاه تست لوکال", "expert_key": "local_expert"},
}

APP_ENV = os.getenv("APP_ENV", "local").strip().lower()
if APP_ENV == "local":
    ADMINS = LOCAL_ADMINS
    SALES_MANAGER = LOCAL_SALES_MANAGER
    SALES_EXPERTS = LOCAL_SALES_EXPERTS
    STORES = LOCAL_STORES


def _fallback_org_data() -> dict:
    return {
        "admins": deepcopy(ADMINS),
        "sales_manager": deepcopy(SALES_MANAGER),
        "sales_experts": deepcopy(SALES_EXPERTS),
        "stores": deepcopy(STORES),
    }


def _active_flag(document: dict) -> bool:
    return bool(document.get("is_active", document.get("active", True)))


def _load_org_data_from_mongo() -> dict:
    try:
        from bot.utils.mongo import get_database

        db = get_database()
        admins = [
            {
                "telegram_id": int(item["telegram_id"]),
                "full_name": item.get("full_name", ""),
                "active": _active_flag(item),
            }
            for item in db["admins"].find({})
            if item.get("telegram_id") is not None and _active_flag(item)
        ]

        managers = [
            item
            for item in db["sales_managers"].find({})
            if item.get("telegram_id") is not None and _active_flag(item)
        ]

        sales_experts = {
            str(item.get("expert_key") or item.get("key")): {
                "telegram_id": int(item["telegram_id"]),
                "full_name": item.get("full_name", ""),
                "active": _active_flag(item),
            }
            for item in db["sales_experts"].find({})
            if (item.get("expert_key") or item.get("key")) and item.get("telegram_id") is not None
        }

        stores = {
            str(item.get("code") or item.get("store_code")): {
                "code": str(item.get("code") or item.get("store_code")),
                "name": item.get("name") or item.get("store_name", ""),
                "expert_key": item.get("expert_key", ""),
                "active": _active_flag(item),
            }
            for item in db["stores"].find({})
            if item.get("code") or item.get("store_code")
        }
    except Exception:
        return {}

    if not admins or not managers or not sales_experts or not stores:
        return {}

    manager = managers[0]
    return {
        "admins": admins,
        "sales_manager": {
            "telegram_id": int(manager["telegram_id"]),
            "full_name": manager.get("full_name", ""),
            "active": _active_flag(manager),
        },
        "sales_experts": sales_experts,
        "stores": stores,
    }


def _org_data() -> dict:
    global _ORG_CACHE, _ORG_CACHE_UNTIL

    now = datetime.utcnow()
    if _ORG_CACHE is not None and _ORG_CACHE_UNTIL and now < _ORG_CACHE_UNTIL:
        return deepcopy(_ORG_CACHE)

    data = _load_org_data_from_mongo() or _fallback_org_data()
    _ORG_CACHE = data
    _ORG_CACHE_UNTIL = now + ORG_CACHE_TTL
    return deepcopy(data)


def clear_org_cache() -> None:
    global _ORG_CACHE, _ORG_CACHE_UNTIL
    _ORG_CACHE = None
    _ORG_CACHE_UNTIL = None


def get_stores() -> dict:
    return _org_data()["stores"]


def get_sales_experts() -> dict:
    return _org_data()["sales_experts"]


def get_sales_manager() -> dict:
    return _org_data()["sales_manager"]


def get_store(code: str):
    return get_stores().get(str(code).strip())


def get_expert_for_store(store_code: str):
    store = get_store(store_code)
    if not store:
        return None
    return get_sales_experts().get(store["expert_key"])


def get_role(telegram_id: int) -> str | None:
    telegram_id = int(telegram_id)
    admins = get_admins()
    sales_manager = get_sales_manager()
    sales_experts = get_sales_experts()
    if any(int(admin["telegram_id"]) == telegram_id for admin in admins):
        return "admin"
    if telegram_id == int(sales_manager["telegram_id"]):
        return "sales_manager"
    for expert in sales_experts.values():
        if telegram_id == int(expert["telegram_id"]):
            return "expert"
    return None


def is_admin(telegram_id: int) -> bool:
    telegram_id = int(telegram_id)
    return any(int(admin["telegram_id"]) == telegram_id for admin in get_admins())


def get_admins() -> list[dict]:
    return _org_data()["admins"]


def get_expert_key_by_telegram_id(telegram_id: int) -> str | None:
    telegram_id = int(telegram_id)
    for key, expert in get_sales_experts().items():
        if telegram_id == int(expert["telegram_id"]):
            return key
    return None


def expert_store_codes(telegram_id: int) -> set[str]:
    expert_key = get_expert_key_by_telegram_id(telegram_id)
    if not expert_key:
        return set()
    return {code for code, store in get_stores().items() if store["expert_key"] == expert_key}
