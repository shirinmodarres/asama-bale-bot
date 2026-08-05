from bale import Message, CallbackQuery

from bot.data.messages import MESSAGES
from bot.data.statuses import status_label
from bot.services.notification_service import format_request, notify_expert_request
from bot.data.statuses import ACTIVE
from bot.utils.keyboards import (
    BTN_ADD_ITEM,
    BTN_CANCEL,
    BTN_EDIT_ITEM,
    BTN_REMOVE_ITEM,
    BTN_SUBMIT,
    BTN_WALLET,
    categories_keyboard,
    draft_items_keyboard,
    products_keyboard,
    quantity_change_keyboard,
    request_review_keyboard,
    seller_main_menu,
    summary_menu,
)
from bot.utils.datetime_format import format_shamsi_datetime
from bot.utils.normalize import normalize_digits
from data.static_data import get_expert_for_store, get_store

# ====== Stateهای مستقل برای درخواست کالا ======
CATEGORY, PRODUCT, QUANTITY, SUMMARY, EDIT_ITEM, EDIT_QUANTITY, REMOVE_ITEM = range(10, 17)


def _format_money(amount: int) -> str:
    return f"{amount:,}"


def _summary(items: list[dict]) -> str:
    lines = [MESSAGES["request_summary"]]
    for index, item in enumerate(items, start=1):
        lines.extend([
            f"{index}) {item['category_name']}",
            f"   مدل: {item['product_model']}",
            f"   تعداد: {item['carton_quantity']} کارتن",
        ])
    return "\n".join(lines)


# ====== ورود به جریان درخواست کالا ======
async def request_goods(message: Message, context: dict):
    user = context["user_service"].get_user(message.author.id)
    if not user or user.get("status") != ACTIVE:
        await message.reply(MESSAGES["not_approved_seller"])
        return
    store = get_store(user["store_code"])
    if store and not store.get("active", True):
        await message.reply(MESSAGES["store_inactive"])
        return
    expert = get_expert_for_store(user["store_code"])
    if not expert or not expert.get("active", True):
        await message.reply(MESSAGES["expert_inactive"])
        return
    context["items"] = []
    context["categories"] = context["product_service"].get_categories()
    await message.reply(
        MESSAGES["choose_category"],
        components=categories_keyboard(context["categories"], navigation_prefix="request"),
    )
    context["state"] = CATEGORY


# ====== انتخاب دسته‌بندی ======
async def choose_category(callback: CallbackQuery, context: dict):
    category_key = callback.data.split(":", 1)[1]
    categories = context["product_service"].get_categories()
    context["categories"] = categories
    context.setdefault("items", [])
    context["category_key"] = category_key
    context["category_name"] = categories[category_key]["name"]
    await callback.message.edit(
        MESSAGES["choose_product"],
        components=products_keyboard(categories, category_key, navigation_prefix="request"),
    )
    context["state"] = PRODUCT


# ====== انتخاب محصول ======
async def choose_product(callback: CallbackQuery, context: dict):
    product_key = callback.data.split(":", 1)[1]
    category_key = context.get("category_key")
    categories = context.get("categories") or context["product_service"].get_categories()
    if not category_key or category_key not in categories:
        await callback.message.edit(MESSAGES.get("stale_button", "این دکمه منقضی شده، لطفاً دوباره «درخواست کالا» را بزنید."))
        return
    context.setdefault("items", [])
    product = categories[category_key]["products"][product_key]
    context["product_key"] = product_key
    context["product_name"] = product["name"]
    context["product_model"] = product["model"]
    await callback.message.edit(MESSAGES["ask_quantity"])
    context["state"] = QUANTITY


# ====== دریافت تعداد ======
async def receive_quantity(message: Message, context: dict):
    text = normalize_digits(message.content)
    if not text.isdigit() or int(text) <= 0:
        await message.reply(MESSAGES["invalid_quantity"])
        return

    if "product_key" not in context or "category_key" not in context:
        await message.reply(
            MESSAGES.get("stale_button", "این مرحله منقضی شده، لطفاً دوباره «درخواست کالا» را بزنید."),
            components=seller_main_menu(),
        )
        context.pop("state", None)
        return

    item = {
        "category_key": context["category_key"],
        "category_name": context["category_name"],
        "product_key": context["product_key"],
        "product_name": context["product_name"],
        "product_model": context["product_model"],
        "carton_quantity": int(text),
    }
    request_service = context["request_service"]
    items = context.setdefault("items", [])
    merged = request_service.merge_draft_item(items, item)
    text = _summary(items)
    if merged:
        text = f"{MESSAGES['item_merged']}\n\n{text}"
    await message.reply(text, components=summary_menu())
    context["state"] = SUMMARY


# ====== افزودن کالای دیگر ======
async def add_item(message: Message, context: dict):
    context["categories"] = context["product_service"].get_categories()
    await message.reply(
        MESSAGES["choose_category"],
        components=categories_keyboard(context["categories"], navigation_prefix="request"),
    )
    context["state"] = CATEGORY


# ====== ویرایش تعداد کالا ======
async def edit_item_menu(message: Message, context: dict):
    await message.reply(
        MESSAGES["select_item_to_edit"],
        components=draft_items_keyboard(context.get("items", []), "edit_item"),
    )
    context["state"] = EDIT_ITEM


async def select_edit_item(callback: CallbackQuery, context: dict):
    index = int(normalize_digits(callback.data.split(":", 1)[1]))
    context["edit_item_index"] = index
    await callback.message.edit(MESSAGES["ask_new_quantity"])
    context["state"] = EDIT_QUANTITY


async def receive_edit_quantity(message: Message, context: dict):
    text = normalize_digits(message.content)
    if not text.isdigit() or int(text) <= 0:
        await message.reply(MESSAGES["invalid_quantity"])
        return
    request_service = context["request_service"]
    request_service.update_draft_item_quantity(
        context["items"],
        context.pop("edit_item_index"),
        int(text),
    )
    await message.reply(_summary(context["items"]), components=summary_menu())
    context["state"] = SUMMARY


# ====== حذف کالا ======
async def remove_item_menu(message: Message, context: dict):
    await message.reply(
        MESSAGES["select_item_to_remove"],
        components=draft_items_keyboard(context.get("items", []), "remove_item"),
    )
    context["state"] = REMOVE_ITEM


async def remove_item(callback: CallbackQuery, context: dict):
    index = int(normalize_digits(callback.data.split(":", 1)[1]))
    request_service = context["request_service"]
    request_service.remove_draft_item(context["items"], index)
    if not context["items"]:
        await callback.message.edit(MESSAGES["no_items_left"])
        context["categories"] = context["product_service"].get_categories()
        await callback.message.reply(
            MESSAGES["choose_category"],
            components=categories_keyboard(context["categories"], navigation_prefix="request"),
        )
        context["state"] = CATEGORY
        return
    await callback.message.edit(MESSAGES["item_removed"])
    await callback.message.reply(_summary(context["items"]), components=summary_menu())
    context["state"] = SUMMARY


# ====== ثبت نهایی درخواست ======
async def submit_request(message: Message, context: dict):
    user_service = context["user_service"]
    request_service = context["request_service"]
    seller = user_service.get_user(message.author.id)
    if not seller or seller.get("role") != "seller" or seller.get("status") != ACTIVE:
        for key in ("items", "category_key", "category_name", "product_key", "product_name", "product_model", "state"):
            context.pop(key, None)
        await message.reply(MESSAGES["not_approved_seller"])
        return

    items = context.get("items") or []
    if not items:
        context.pop("state", None)
        await message.reply(MESSAGES["no_items_left"], components=seller_main_menu())
        return

    store_code = seller.get("store_code")
    store = get_store(store_code)
    if not store:
        for key in ("items", "category_key", "category_name", "product_key", "product_name", "product_model", "state"):
            context.pop(key, None)
        await message.reply(MESSAGES["invalid_store_code"], components=seller_main_menu())
        return

    if store and not store.get("active", True):
        for key in ("items", "category_key", "category_name", "product_key", "product_name", "product_model", "state"):
            context.pop(key, None)
        await message.reply(MESSAGES["store_inactive"], components=seller_main_menu())
        return

    expert = get_expert_for_store(store_code)
    if not expert or not expert.get("active", True):
        for key in ("items", "category_key", "category_name", "product_key", "product_name", "product_model", "state"):
            context.pop(key, None)
        await message.reply(MESSAGES["expert_inactive"], components=seller_main_menu())
        return

    request = request_service.create_request(seller, expert, items)
    await notify_expert_request(context, expert, request)
    # پاک کردن فقط داده‌های مربوط به درخواست
    for key in ("items", "category_key", "category_name", "product_key", "product_name", "product_model", "state"):
        context.pop(key, None)
    await message.reply(MESSAGES["request_submitted"], components=seller_main_menu())


# ====== لغو درخواست ======
async def cancel_request(message: Message, context: dict):
    for key in ("items", "category_key", "category_name", "product_key", "product_name", "product_model", "state"):
        context.pop(key, None)
    await message.reply(MESSAGES["request_cancelled"], components=seller_main_menu())


# ====== مشاهده درخواست‌های من ======
async def my_requests(message: Message, context: dict):
    request_service = context["request_service"]
    requests = request_service.list_requests_for_seller(message.author.id)
    if not requests:
        await message.reply(MESSAGES["no_requests"])
        return
    lines = [MESSAGES["my_requests"]]
    for request in requests[-10:]:
        lines.extend([
            "",
            f"درخواست #{request['id']}",
            f"وضعیت: {status_label(request['status'])}",
        ])
        for index, item in enumerate(request.get("items", []), start=1):
            lines.append(
                f"{index}) {item['category_name']} - مدل {item['product_model']} - {item['carton_quantity']} کارتن"
            )
        reason = request.get("expert_reject_reason") or request.get("manager_reject_reason")
        if reason:
            lines.append(f"علت رد: {reason}")
    await message.reply("\n".join(lines))


# ====== تغییر تعداد توسط کارشناس (callback از seller) ======
async def quantity_change_callback(callback: CallbackQuery, context: dict):
    _prefix, action, request_id_text, index_text = callback.data.split(":")
    request_id = int(normalize_digits(request_id_text))
    index = int(normalize_digits(index_text))

    request_service = context["request_service"]
    request = request_service.get_request(request_id)
    if not request or request["seller_telegram_id"] != callback.from_user.id:
        await callback.message.edit(MESSAGES["quantity_change_not_found"])
        return

    items = request.get("items", [])
    if index < 0 or index >= len(items) or items[index].get("quantity_change_status") != "pending":
        await callback.message.edit(MESSAGES["quantity_change_not_found"])
        return

    item = items[index]
    product_model = item["product_model"]

    if action == "approve":
        new_quantity = item.get("pending_quantity")
        request = request_service.confirm_item_quantity_change(request_id, index)
        await callback.message.edit(MESSAGES["quantity_change_confirmed_to_seller"])
        await context["bot"].send_message(
            request["expert_telegram_id"],
            MESSAGES["quantity_change_confirmed_notify_expert"].format(
                request_id=request_id,
                product_model=product_model,
                quantity=new_quantity,
            ),
        )
        await context["bot"].send_message(
            request["expert_telegram_id"],
            format_request(request, MESSAGES["request_needs_expert_review_again"]),
            components=request_review_keyboard(request["id"], request.get("items", [])),
        )
        return

    old_quantity = item["carton_quantity"]
    request = request_service.reject_item_quantity_change(request_id, index)
    await callback.message.edit(MESSAGES["quantity_change_rejected_to_seller"])
    await context["bot"].send_message(
        request["expert_telegram_id"],
        MESSAGES["quantity_change_rejected_notify_expert"].format(
            request_id=request_id,
            product_model=product_model,
            quantity=old_quantity,
        ),
    )


# ====== نمایش کیف پول ======
async def show_wallet(message: Message, context: dict):
    user_service = context["user_service"]
    user = user_service.get_user(message.author.id)
    if not user or user.get("status") != ACTIVE:
        await message.reply(MESSAGES["not_approved_seller"])
        return

    wallet = user_service.get_wallet(message.author.id)
    lines = [
        MESSAGES["wallet_title"],
        MESSAGES["wallet_balance"].format(balance=_format_money(wallet["balance"])),
        "",
    ]
    transactions = wallet.get("transactions", [])[-5:]
    if not transactions:
        lines.append(MESSAGES["wallet_no_transactions"])
    else:
        lines.append(MESSAGES["wallet_last_transactions"])
        for transaction in reversed(transactions):
            lines.append(MESSAGES["wallet_transaction_line"].format(
                date=format_shamsi_datetime(transaction.get("created_at", "")),
                amount=_format_money(transaction.get("amount", 0)),
                description=transaction.get("description", ""),
            ))
    await message.reply("\n".join(lines), components=seller_main_menu())
