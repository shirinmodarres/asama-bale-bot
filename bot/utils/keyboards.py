from bale import InlineKeyboardButton, InlineKeyboardMarkup, MenuKeyboardMarkup, MenuKeyboardButton

from bot.data.messages import MESSAGES
from data.static_data import CATEGORIES

# ============================================================
# ثابت‌های متنی (همان‌طور که در هندلرها استفاده می‌شوند)
# ============================================================

BTN_REQUEST_GOODS = "درخواست کالا"
BTN_MY_REQUESTS = "درخواست‌های من"
BTN_ADD_ITEM = "افزودن کالای دیگر"
BTN_EDIT_ITEM = "ویرایش تعداد کالا"
BTN_REMOVE_ITEM = "حذف کالا"
BTN_SUBMIT = "ثبت نهایی درخواست"
BTN_CANCEL = "لغو"
BTN_EXPORT = "خروجی اکسل"
BTN_INFO = "اطلاعات ربات"
BTN_EDIT_SELLER = "ویرایش مشخصات فروشنده"
BTN_CREATE_ORDER = "ثبت سریال"
BTN_WALLET = "کیف پول"
BTN_EXPORT_ORDERS = "خروجی اکسل سفارش‌ها"
BTN_PENDING_REQUESTS = "درخواست‌های در انتظار بررسی"
BTN_PENDING_ORDERS = "سفارش‌های در انتظار اعتبارسنجی"
BTN_ADMIN_MANAGEMENT = "پنل مدیریت"
BTN_ADMIN_MANAGE_PRODUCTS = "مدیریت کالاها"
BTN_ADMIN_MANAGE_STORES = "مدیریت فروشگاه‌ها"
BTN_ADMIN_MANAGE_EXPERTS = "مدیریت کارشناسان"
BTN_ADMIN_MANAGE_BOT = "مدیریت ربات"
BTN_ADMIN_ACTION_REQUESTS = "درخواست‌های مدیریتی"
BTN_ADMIN_ACTIVE_PRODUCTS = "کالاهای فعال"
BTN_ADMIN_INACTIVE_PRODUCTS = "کالاهای غیرفعال"
BTN_ADMIN_STORE_LIST = "فهرست فروشگاه‌ها"
BTN_ADMIN_EXPERT_LIST = "فهرست کارشناسان"
BTN_ADMIN_ACTIVE_STORES = "فروشگاه‌های فعال"
BTN_ADMIN_INACTIVE_STORES = "فروشگاه‌های غیرفعال"
BTN_ADMIN_ACTIVE_EXPERTS = "کارشناسان فعال"
BTN_ADMIN_INACTIVE_EXPERTS = "کارشناسان غیرفعال"
BTN_ADMIN_DISABLE_BOT = "خاموش کردن ربات"
BTN_ADMIN_ENABLE_BOT = "روشن کردن ربات"
BTN_BACK = "بازگشت"
BTN_PRODUCT_MANAGEMENT = BTN_ADMIN_MANAGE_PRODUCTS
BTN_STORE_MANAGEMENT = BTN_ADMIN_MANAGE_STORES
BTN_EXPERT_MANAGEMENT = BTN_ADMIN_MANAGE_EXPERTS
BTN_BOT_MANAGEMENT = BTN_ADMIN_MANAGE_BOT
BTN_PENDING_ADMIN_ACTIONS = BTN_ADMIN_ACTION_REQUESTS
BTN_ENABLE = "روشن"
BTN_DISABLE = "خاموش"


# ============================================================
# MenuKeyboard (کیبوردهای معمولی)
# ============================================================

def seller_main_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_CREATE_ORDER), row=1)
    markup.add(MenuKeyboardButton(BTN_REQUEST_GOODS), row=2)
    markup.add(MenuKeyboardButton(BTN_MY_REQUESTS), row=3)
    markup.add(MenuKeyboardButton(BTN_WALLET), row=4)
    return markup


def expert_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_PENDING_REQUESTS), row=1)
    markup.add(MenuKeyboardButton(BTN_PENDING_ORDERS), row=2)
    markup.add(MenuKeyboardButton(BTN_EDIT_SELLER), row=3)
    markup.add(MenuKeyboardButton(BTN_EXPORT), row=4)
    return markup


def sales_manager_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_ADMIN_MANAGEMENT), row=1)
    markup.add(MenuKeyboardButton(BTN_EXPORT), row=2)
    markup.add(MenuKeyboardButton(BTN_EXPORT_ORDERS), row=3)
    return markup


def admin_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_ADMIN_MANAGEMENT), row=1)
    markup.add(MenuKeyboardButton(BTN_INFO), row=2)
    markup.add(MenuKeyboardButton(BTN_EXPORT), row=3)
    markup.add(MenuKeyboardButton(BTN_EXPORT_ORDERS), row=4)
    return markup


def admin_management_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_ADMIN_MANAGE_PRODUCTS), row=1)
    markup.add(MenuKeyboardButton(BTN_ADMIN_MANAGE_STORES), row=2)
    markup.add(MenuKeyboardButton(BTN_ADMIN_MANAGE_EXPERTS), row=3)
    markup.add(MenuKeyboardButton(BTN_ADMIN_MANAGE_BOT), row=4)
    markup.add(MenuKeyboardButton(BTN_ADMIN_ACTION_REQUESTS), row=5)
    markup.add(MenuKeyboardButton(BTN_BACK), row=6)
    return markup


def admin_products_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_ADMIN_ACTIVE_PRODUCTS), row=1)
    markup.add(MenuKeyboardButton(BTN_ADMIN_INACTIVE_PRODUCTS), row=2)
    markup.add(MenuKeyboardButton(BTN_BACK), row=3)
    return markup


def admin_stores_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_ADMIN_ACTIVE_STORES), row=1)
    markup.add(MenuKeyboardButton(BTN_ADMIN_INACTIVE_STORES), row=2)
    markup.add(MenuKeyboardButton(BTN_BACK), row=3)
    return markup


def admin_experts_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_ADMIN_ACTIVE_EXPERTS), row=1)
    markup.add(MenuKeyboardButton(BTN_ADMIN_INACTIVE_EXPERTS), row=2)
    markup.add(MenuKeyboardButton(BTN_BACK), row=3)
    return markup


def admin_bot_menu(active: bool):
    markup = MenuKeyboardMarkup()
    if active:
        markup.add(MenuKeyboardButton(BTN_ADMIN_DISABLE_BOT), row=1)
    else:
        markup.add(MenuKeyboardButton(BTN_ADMIN_ENABLE_BOT), row=1)
    markup.add(MenuKeyboardButton(BTN_BACK), row=2)
    return markup


def summary_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_ADD_ITEM), row=1)
    markup.add(MenuKeyboardButton(BTN_EDIT_ITEM), row=2)
    markup.add(MenuKeyboardButton(BTN_REMOVE_ITEM), row=3)
    markup.add(MenuKeyboardButton(BTN_SUBMIT), row=4)
    markup.add(MenuKeyboardButton(BTN_CANCEL), row=5)
    return markup


# ============================================================
# InlineKeyboard (کیبوردهای اینلاین)
# ============================================================

def categories_keyboard(include_inactive_products: bool = False, navigation_prefix: str | None = None):
    markup = InlineKeyboardMarkup()
    row = 1
    for category_key, category in CATEGORIES.items():
        products = category.get("products", {})
        if not include_inactive_products:
            products = {k: v for k, v in products.items() if v.get("active", True)}
            if not products:
                continue
        markup.add(InlineKeyboardButton(category["name"], callback_data=f"cat:{category_key}"), row=row)
        row += 1
    if navigation_prefix:
        markup.add(InlineKeyboardButton(BTN_BACK, callback_data=f"{navigation_prefix}_nav:back"), row=row)
    return markup


def products_keyboard(category_key: str, include_inactive: bool = False, navigation_prefix: str | None = None):
    products = CATEGORIES[category_key]["products"]
    if not include_inactive:
        products = {k: v for k, v in products.items() if v.get("active", True)}
    markup = InlineKeyboardMarkup()
    for idx, (product_key, product) in enumerate(products.items(), start=1):
        markup.add(
            InlineKeyboardButton(
                f"{product['model']} | کد {product['code']}",
                callback_data=f"prod:{product_key}"
            ),
            row=idx
        )
    if navigation_prefix:
        markup.add(InlineKeyboardButton(BTN_BACK, callback_data=f"{navigation_prefix}_nav:back"), row=len(products) + 1)
    return markup


def order_text_navigation_menu():
    markup = MenuKeyboardMarkup()
    markup.add(MenuKeyboardButton(BTN_BACK), row=1)
    return markup


def approval_keyboard(prefix: str, item_id: int):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("تأیید", callback_data=f"{prefix}:approve:{item_id}"), row=1)
    markup.add(InlineKeyboardButton("رد", callback_data=f"{prefix}:reject:{item_id}"), row=2)
    return markup


def request_review_keyboard(request_id: int, items: list[dict] | None = None):
    markup = InlineKeyboardMarkup()
    total_cartons = sum(item.get("carton_quantity", 0) for item in (items or []))
    edit_label = f"✏️ ویرایش تعداد ({total_cartons} کارتن)" if items else "✏️ ویرایش تعداد"
    markup.add(InlineKeyboardButton("تأیید", callback_data=f"expert:approve:{request_id}"), row=1)
    markup.add(InlineKeyboardButton("رد", callback_data=f"expert:reject:{request_id}"), row=2)
    markup.add(InlineKeyboardButton(edit_label, callback_data=f"expert:edit:{request_id}"), row=3)
    return markup


def request_items_edit_keyboard(request_id: int, items: list[dict]):
    markup = InlineKeyboardMarkup()
    for idx, item in enumerate(items, start=1):
        markup.add(
            InlineKeyboardButton(
                f"{idx}. {item['product_model']} - {item['carton_quantity']} کارتن",
                callback_data=f"expert_edit_item:{request_id}:{idx-1}",
            ),
            row=idx
        )
    return markup


def quantity_change_keyboard(request_id: int, index: int):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("تأیید", callback_data=f"qty_change:approve:{request_id}:{index}"), row=1)
    markup.add(InlineKeyboardButton("رد", callback_data=f"qty_change:reject:{request_id}:{index}"), row=2)
    return markup


def order_unit_validation_keyboard(order_id: str, unit_index: int):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("تأیید کالا", callback_data=f"order_unit:approve:{order_id}:{unit_index}"), row=1)
    markup.add(InlineKeyboardButton("رد کالا", callback_data=f"order_unit:reject:{order_id}:{unit_index}"), row=2)
    return markup


def stores_keyboard(stores: list[dict], prefix: str, back_callback: str | None = None):
    markup = InlineKeyboardMarkup()
    for idx, store in enumerate(stores, start=1):
        markup.add(
            InlineKeyboardButton(
                f"{store['code']} - {store['name']}",
                callback_data=f"{prefix}:{store['code']}"
            ),
            row=idx
        )
    if back_callback:
        markup.add(InlineKeyboardButton(BTN_BACK, callback_data=back_callback), row=len(stores) + 1)
    return markup


def experts_keyboard(experts: list[dict], prefix: str, back_callback: str | None = None):
    markup = InlineKeyboardMarkup()
    for idx, expert in enumerate(experts, start=1):
        markup.add(
            InlineKeyboardButton(
                f"{expert['expert_key']} - {expert['full_name']}",
                callback_data=f"{prefix}:{expert['expert_key']}"
            ),
            row=idx
        )
    if back_callback:
        markup.add(InlineKeyboardButton(BTN_BACK, callback_data=back_callback), row=len(experts) + 1)
    return markup


def product_status_keyboard(products: list[dict], back_callback: str | None = None):
    markup = InlineKeyboardMarkup()
    for idx, product in enumerate(products, start=1):
        markup.add(
            InlineKeyboardButton(
                f"{product['model']} | کد {product['code']}",
                callback_data=f"admin:product_select:{product['category_key']}:{product['product_key']}"
            ),
            row=idx,
        )
    if back_callback:
        markup.add(InlineKeyboardButton(BTN_BACK, callback_data=back_callback), row=len(products) + 1)
    return markup


def product_action_keyboard(category_key: str, product_key: str, active: bool, back_callback: str | None = None):
    markup = InlineKeyboardMarkup()
    if active:
        markup.add(
            InlineKeyboardButton(MESSAGES["admin_product_disable"], callback_data=f"admin:product_toggle:{category_key}:{product_key}:0"),
            row=1,
        )
    else:
        markup.add(
            InlineKeyboardButton(MESSAGES["admin_product_enable"], callback_data=f"admin:product_toggle:{category_key}:{product_key}:1"),
            row=1,
        )
    if back_callback:
        markup.add(InlineKeyboardButton(BTN_BACK, callback_data=back_callback), row=2)
    return markup


def store_action_keyboard(store_code: str, active: bool, back_callback: str | None = None):
    markup = InlineKeyboardMarkup()
    if active:
        markup.add(
            InlineKeyboardButton(MESSAGES["admin_product_disable"], callback_data=f"admin:store_toggle:{store_code}:0"),
            row=1,
        )
    else:
        markup.add(
            InlineKeyboardButton(MESSAGES["admin_product_enable"], callback_data=f"admin:store_toggle:{store_code}:1"),
            row=1,
        )
    if back_callback:
        markup.add(InlineKeyboardButton(BTN_BACK, callback_data=back_callback), row=2)
    return markup


def expert_action_keyboard(expert_key: str, active: bool, back_callback: str | None = None):
    markup = InlineKeyboardMarkup()
    if active:
        markup.add(
            InlineKeyboardButton(MESSAGES["admin_product_disable"], callback_data=f"admin:expert_toggle:{expert_key}:0"),
            row=1,
        )
    else:
        markup.add(
            InlineKeyboardButton(MESSAGES["admin_product_enable"], callback_data=f"admin:expert_toggle:{expert_key}:1"),
            row=1,
        )
    if back_callback:
        markup.add(InlineKeyboardButton(BTN_BACK, callback_data=back_callback), row=2)
    return markup


def admin_action_requests_keyboard(requests: list[dict]):
    markup = InlineKeyboardMarkup()
    for idx, request in enumerate(requests, start=1):
        markup.add(
            InlineKeyboardButton(
                f"#{request['id']} - {request['title']} ({request['status']})",
                callback_data=f"admin:request:{request['id']}"
            ),
            row=idx,
        )
    return markup


def admin_action_request_detail_keyboard(request: dict):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            f"#{request['id']} - {request['title']} ({request['status']})",
            callback_data=f"admin:request:{request['id']}"
        ),
        row=1,
    )
    if request.get("status") == "pending":
        markup.add(InlineKeyboardButton("تأیید", callback_data=f"admin:approve:{request['id']}"), row=2)
        markup.add(InlineKeyboardButton("رد", callback_data=f"admin:reject:{request['id']}"), row=3)
    return markup


def order_rejection_reasons_keyboard():
    from bot.data.messages import VALIDATION_REJECTION_REASONS
    markup = InlineKeyboardMarkup()
    for idx, (key, text) in enumerate(VALIDATION_REJECTION_REASONS.items(), start=1):
        markup.add(InlineKeyboardButton(text, callback_data=f"order_reject_reason:{key}"), row=idx)
    return markup


def order_edit_keyboard():
    return InlineKeyboardMarkup()


def order_units_keyboard(units: list[dict]):
    markup = InlineKeyboardMarkup()
    for idx, unit in enumerate(units, start=1):
        markup.add(
            InlineKeyboardButton(
                f"کالای شماره {unit['index']}",
                callback_data=f"order_edit_unit:{unit['index']}"
            ),
            row=idx
        )
    markup.add(InlineKeyboardButton(BTN_BACK, callback_data="order_back"), row=len(units) + 1)
    return markup


def order_unit_field_keyboard(unit_index: int):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("کد رهگیری", callback_data=f"order_edit_tracking:{unit_index}"), row=1)
    markup.add(InlineKeyboardButton("عکس فاکتور", callback_data=f"order_edit_factor:{unit_index}"), row=2)
    markup.add(InlineKeyboardButton(BTN_BACK, callback_data="order_back"), row=3)
    return markup


def draft_items_keyboard(items: list[dict], prefix: str):
    markup = InlineKeyboardMarkup()
    for idx, item in enumerate(items, start=1):
        markup.add(
            InlineKeyboardButton(
                f"{idx}. {item['product_model']} - {item['carton_quantity']} کارتن",
                callback_data=f"{prefix}:{idx-1}",
            ),
            row=idx
        )
    return markup


def seller_edit_keyboard(sellers: list[dict]):
    markup = InlineKeyboardMarkup()
    for idx, seller in enumerate(sellers, start=1):
        markup.add(
            InlineKeyboardButton(
                f"{seller['store_code']} - {seller['full_name']}",
                callback_data=f"edit_seller:{seller['telegram_id']}",
            ),
            row=idx
        )
    return markup


def seller_edit_field_keyboard(telegram_id: int):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("ویرایش نام", callback_data=f"edit_seller_name:{telegram_id}"), row=1)
    markup.add(InlineKeyboardButton("ویرایش موبایل", callback_data=f"edit_seller_phone:{telegram_id}"), row=2)
    return markup


# ============================================================
# کیبورد اینلاین برای خلاصه سفارش (ثبت سریال)
# ============================================================
def order_validation_inline_keyboard():
    from bot.data.messages import MESSAGES
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(MESSAGES["order_submit"], callback_data="order_submit"), row=1)
    markup.add(InlineKeyboardButton(MESSAGES["order_edit"], callback_data="order_edit"), row=2)
    markup.add(InlineKeyboardButton(BTN_BACK, callback_data="order_back"), row=3)
    return markup
