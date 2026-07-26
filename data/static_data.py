"""
Single source of manually maintained MVP data.

Edit Telegram IDs, stores, experts, manager/admin, categories, and products here.
Do not hardcode this data inside handlers.
"""

ADMINS = [
    {"telegram_id": 700144333, "full_name": "System Manager"},
    {"telegram_id": 583160697, "full_name": "Admin 2"},
]

BOT_ACTIVE = True

SALES_MANAGER = {
    "telegram_id": 132500720,
    "full_name": "Sales Manager",
}

SALES_EXPERTS = {
    "expert_1": {
        "telegram_id": 1622824763,
        "full_name": "آقای کوهی ",
    },
    "expert_2": {
        "telegram_id": 838414503,
        "full_name": "خانم مدیری",
    },
}

STORES = {
    "1": {"code": "23", "name": "فتح المبین(شیراز)", "expert_key": "expert_1"},
    "2": {"code": "22", "name": "سنندج", "expert_key": "expert_1"},
    "3": {"code": "21", "name": "گرگان", "expert_key": "expert_1"},
    "4": {"code": "20", "name": "شاهین شهر", "expert_key": "expert_1"},
    "5": {"code": "19", "name": "اهواز", "expert_key": "expert_1"},
    "6": {"code": "18", "name": "بیرجند", "expert_key": "expert_1"},
    "7": {"code": "3", "name": "تبریز", "expert_key": "expert_1"},
    "8": {"code": "17", "name": "زنجان", "expert_key": "expert_1"},
    "9": {"code": "6", "name": "فلاحی", "expert_key": "expert_1"},
    "10": {"code": "5", "name": "رشت", "expert_key": "expert_1"},
    "11": {"code": "16", "name": "شهرکرد", "expert_key": "expert_1"},
    "12": {"code": "15", "name": "اراک", "expert_key": "expert_1"},
    "13": {"code": "14", "name": "یاسوج", "expert_key": "expert_1"},
    "14": {"code": "2", "name": "کرج", "expert_key": "expert_1"},
    "15": {"code": "13", "name": "اردبیل", "expert_key": "expert_1"},
    "16": {"code": "6", "name": "شهدای انقلاب", "expert_key": "expert_1"},
    "17": {"code": "1", "name": "فکوری", "expert_key": "expert_1"},
    "18": {"code": "7", "name": "امامی نسب", "expert_key": "expert_1"},
    "19": {"code": "9", "name": "فردیس", "expert_key": "expert_1"},
    "20": {"code": "8", "name": "لویزان", "expert_key": "expert_1"},
    "21": {"code": "10", "name": "شهید محلاتی", "expert_key": "expert_1"},
    "22": {"code": "11", "name": "مراغه", "expert_key": "expert_1"},
    "23": {"code": "12", "name": "رودهن", "expert_key": "expert_1"},
    "24": {"code": "25", "name": "رجایی", "expert_key": "expert_2"},
    "25": {"code": "39", "name": "ارومیه", "expert_key": "expert_2"},
    "26": {"code": "38", "name": "دزفول", "expert_key": "expert_2"},
    "27": {"code": "37", "name": "قصر فیروزه", "expert_key": "expert_2"},
    "28": {"code": "36", "name": "ایلام", "expert_key": "expert_2"},
    "29": {"code": "26", "name": "کرمانشاه مرکزی", "expert_key": "expert_2"},
    "30": {"code": "35", "name": "قزوین", "expert_key": "expert_2"},
    "31": {"code": "34", "name": "همدان", "expert_key": "expert_2"},
    "32": {"code": "27", "name": "اصفهان", "expert_key": "expert_2"},
    "33": {"code": "28", "name": "زاهدان", "expert_key": "expert_2"},
    "34": {"code": "33", "name": "یزد", "expert_key": "expert_2"},
    "35": {"code": "32", "name": "بجنورد", "expert_key": "expert_2"},
    "36": {"code": "29", "name": "ساری", "expert_key": "expert_2"},
    "37": {"code": "30", "name": "سمنان", "expert_key": "expert_2"},
    "38": {"code": "31", "name": "قم", "expert_key": "expert_2"},
    "39": {"code": "24", "name": "چمران", "expert_key": "expert_2"},
}

CATEGORIES = {
"grinder": {
"name": "آسیاب",
"products": {
"12100235": {"name": "آسیاب و خردکن 800 وات مدل 321-N", "model": "321-N", "code": "12100235", "price": 4890000},
"12100238": {"name": "آسیاب و خردکن 800 وات مدل 322-N", "model": "322-N", "code": "12100238", "price": 5650000},
"12100239": {"name": "آسیاب و خرد کن 350 وات کاسه دار مدل 310-A مشکی", "model": "310-A", "code": "12100239", "price": 5580000},
"12100246": {"name": "آسیاب قهوه 150 وات مدل N95", "model": "N95", "code": "12100246", "price": 2950000},
},
},
"mixer_blender": {
"name": "مخلوط کن",
"products": {
"12100249": {"name": "مخلوط کن / بلندر مدل 395-N", "model": "395-N", "code": "12100249", "price": 3340000},
},
},
"mixer": {
"name": "همزن",
"products": {
"12100255": {"name": "غذاساز چند کاره روند و مدل N400", "model": "N400", "code": "12100255", "price": 5510000},
"12100253": {"name": "همزن مدل 645", "model": "645", "code": "12100253", "price": 3490000},
"12100252": {"name": "همزن دستی مدل 644", "model": "644", "code": "12100252", "price": 3860000},
"12100251": {"name": "همزن چهار تیغه مدل 656", "model": "656", "code": "12100251", "price": 3950000},
},
},
"hand_blender": {
"name": "گوشت کوب",
"products": {
"12100270": {"name": "گوشت کوب برقی 200 وات تک کاره مدل 510-NHB", "model": "510-NHB", "code": "12100270", "price": 3560000},
"12100269": {"name": "گوشت کوب برقی دو تیغه مدل 520", "model": "520", "code": "12100269", "price": 7000000},
},
},
"juicer": {
"name": "آبمیوه گیری",
"products": {
"MJ176": {"name": "آبمیوه گیری سه کاره مدل MJ176", "model": "MJ176", "code": "12400366", "price": 6340000},
"178-N": {"name": "آبمیوه گیری چهار کاره مدل 178-N", "model": "178-N", "code": "12400363", "price": 16160000},
"NJ22": {"name": "آب مرکبات گیر مدل NJ22", "model": "NJ22", "code": "12400697", "price": 2910000},
},
},
"vacuum_cleaner": {
"name": "جاروبرقی",
"products": {
"NCV-9870": {"name": "جاروبرقی 2200 وات مدل NCV-9870", "model": "NCV-9870", "code": "12200319", "price": 27280000},
},
},
"meat_grinder": {
"name": "چرخ گوشت",
"products": {
"MKG50": {"name": "چرخ گوشت 1500 وات مدل MKG50", "model": "MKG50", "code": "12100265", "price": 14310000},
"MKG70": {"name": "چرخ گوشت 2000 وات مدل MKG70", "model": "MKG70", "code": "12100268", "price": 19290000},
"MKG60": {"name": "چرخ گوشت 2000 وات مدل MKG60", "model": "MKG60", "code": "12100267", "price": 19560000},
},
},
"fan": {
"name": "پنکه",
"products": {
"NSF4035": {"name": "پنکه پایه بلند 55 وات مدل NSF4035", "model": "NSF4035", "code": "12500384", "price": 9010000},
},
},
"tea_maker": {
"name": "چای ساز",
"products": {
"NTM4110": {"name": "چای ساز مدل NTM4110", "model": "NTM4110", "code": "12400356", "price": 9810000},
"NTM4200": {"name": "چای ساز مدل NTM4200", "model": "NTM4200", "code": "12400354", "price": 9920000},
"NTM5000": {"name": "چای ساز مدل NTM5000", "model": "NTM5000", "code": "12400357", "price": 10120000},
},
},
}

def get_store(code: str):
    return STORES.get(str(code).strip())


def get_expert_for_store(store_code: str):
    store = get_store(store_code)
    if not store:
        return None
    return SALES_EXPERTS.get(store["expert_key"])


def get_role(telegram_id: int) -> str | None:
    if any(admin["telegram_id"] == telegram_id for admin in ADMINS):
        return "admin"
    if telegram_id == SALES_MANAGER["telegram_id"]:
        return "sales_manager"
    for expert in SALES_EXPERTS.values():
        if telegram_id == expert["telegram_id"]:
            return "expert"
    return None


def is_admin(telegram_id: int) -> bool:
    return any(admin["telegram_id"] == telegram_id for admin in ADMINS)


def get_admins() -> list[dict]:
    return ADMINS


def get_expert_key_by_telegram_id(telegram_id: int) -> str | None:
    for key, expert in SALES_EXPERTS.items():
        if telegram_id == expert["telegram_id"]:
            return key
    return None


def expert_store_codes(telegram_id: int) -> set[str]:
    expert_key = get_expert_key_by_telegram_id(telegram_id)
    if not expert_key:
        return set()
    return {code for code, store in STORES.items() if store["expert_key"] == expert_key}
