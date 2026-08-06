from bale import Message, CallbackQuery

from bot.data.messages import MESSAGES
from bot.data.statuses import PENDING_EXPERT, PENDING_SELLER_APPROVAL
from bot.services.notification_service import format_request
from bot.utils.keyboards import (
    approval_keyboard,
    quantity_change_keyboard,
    request_items_edit_keyboard,
    request_review_keyboard,
    seller_edit_field_keyboard,
    seller_edit_keyboard,
    seller_main_menu,
)
from bot.utils.normalize import normalize_digits
from bot.utils.validators import normalize_mobile
from data.static_data import expert_store_codes, get_role

(
    EXPERT_REJECT_REASON,
    EDIT_SELLER_PICK,
    EDIT_SELLER_FIELD,
    EDIT_SELLER_NAME,
    EDIT_SELLER_PHONE,
    EXPERT_EDIT_ITEM,
    EXPERT_EDIT_QUANTITY,
) = range(20, 27)


async def seller_approval_callback(callback: CallbackQuery, context: dict):
    if get_role(callback.from_user.id) != "expert":
        await callback.message.edit(MESSAGES["not_allowed"])
        return

    _prefix, action, seller_id_text = callback.data.split(":")
    seller_id = int(normalize_digits(seller_id_text))
    user_service = context["user_service"]
    seller = user_service.get_user(seller_id)
    if not seller or seller["store_code"] not in expert_store_codes(callback.from_user.id):
        await callback.message.edit(MESSAGES["seller_not_for_expert"])
        return
    if seller.get("status") != PENDING_SELLER_APPROVAL:
        await callback.message.edit(MESSAGES["seller_approval_already_processed"])
        return

    if action == "approve":
        seller = user_service.approve_seller(seller_id)
        await context["bot"].send_message(seller_id, MESSAGES["seller_approved"], components=seller_main_menu())
        await callback.message.edit(MESSAGES["seller_approved_by_expert"])
    else:
        user_service.reject_seller(seller_id)
        await context["bot"].send_message(seller_id, MESSAGES["seller_rejected_notify"])
        await callback.message.edit(MESSAGES["seller_rejected_by_expert"])


async def pending_requests(message: Message, context: dict):
    if get_role(message.author.id) != "expert":
        await message.reply(MESSAGES["not_allowed"])
        return
    requests = context["request_service"].list_pending_for_stores(
        expert_store_codes(message.author.id)
    )
    if not requests:
        await message.reply(MESSAGES["no_pending_requests"])
        return
    await message.reply(MESSAGES["pending_requests"])
    for request in requests:
        await message.reply(
            format_request(request, f"درخواست #{request['id']}"),
            components=request_review_keyboard(request["id"], request.get("items", [])),
        )


async def expert_request_callback(callback: CallbackQuery, context: dict):
    if get_role(callback.from_user.id) != "expert":
        await callback.message.edit(MESSAGES["not_allowed"])
        return

    _prefix, action, request_id_text = callback.data.split(":")
    request_id = int(normalize_digits(request_id_text))
    request_service = context["request_service"]
    request = request_service.get_request(request_id)
    if not request or request["store_code"] not in expert_store_codes(callback.from_user.id):
        await callback.message.edit(MESSAGES["request_not_for_expert"])
        return
    if request.get("status") != PENDING_EXPERT:
        await callback.message.edit(MESSAGES["request_already_processed"])
        return

    if action == "approve":
        request = request_service.finalize_request(request_id)
        await context["bot"].send_message(
            request["seller_telegram_id"],
            MESSAGES["request_finalized_by_expert"],
        )
        await callback.message.edit(MESSAGES["request_finalized_done_for_expert"])
        return

    if action == "edit":
        context["expert_edit_request_id"] = request_id
        await callback.message.edit(
            MESSAGES["select_request_item_to_edit"],
            components=request_items_edit_keyboard(request_id, request.get("items", [])),
        )
        context["state"] = EXPERT_EDIT_ITEM
        return

    context["expert_reject_request_id"] = request_id
    await callback.message.edit(MESSAGES["ask_reject_reason"])
    context["state"] = EXPERT_REJECT_REASON


async def pick_request_item_to_edit(callback: CallbackQuery, context: dict):
    _prefix, request_id_text, index_text = callback.data.split(":")
    request_id = int(normalize_digits(request_id_text))
    index = int(normalize_digits(index_text))

    request_service = context["request_service"]
    request = request_service.get_request(request_id)
    if not request or request["store_code"] not in expert_store_codes(callback.from_user.id):
        await callback.message.edit(MESSAGES["request_not_for_expert"])
        return

    context["expert_edit_request_id"] = request_id
    context["expert_edit_item_index"] = index
    await callback.message.edit(MESSAGES["ask_new_request_item_quantity"])
    context["state"] = EXPERT_EDIT_QUANTITY


async def receive_request_item_quantity(message: Message, context: dict):
    text = normalize_digits(message.content)
    if not text.isdigit() or int(text) <= 0:
        await message.reply(MESSAGES["invalid_quantity"])
        return

    request_id = context.pop("expert_edit_request_id", None)
    index = context.pop("expert_edit_item_index", None)
    if request_id is None or index is None:
        await message.reply(MESSAGES["request_not_found"])
        return

    new_quantity = int(text)

    request_service = context["request_service"]
    request = request_service.get_request(request_id)
    if not request or request["store_code"] not in expert_store_codes(message.author.id):
        await message.reply(MESSAGES["request_not_for_expert"])
        return

    items = request.get("items", [])
    if index < 0 or index >= len(items):
        await message.reply(MESSAGES["request_not_found"])
        return

    item = items[index]
    old_quantity = item["carton_quantity"]
    product_model = item["product_model"]

    request = request_service.propose_item_quantity_change(request_id, index, new_quantity)
    if not request:
        await message.reply(MESSAGES["request_not_found"])
        return

    await context["bot"].send_message(
        request["seller_telegram_id"],
        MESSAGES["quantity_change_request_to_seller"].format(
            request_id=request_id,
            product_model=product_model,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
        ),
        components=quantity_change_keyboard(request_id, index),
    )

    await message.reply(MESSAGES["quantity_change_sent_to_seller"])
    context.pop("state", None)


async def receive_expert_reject_reason(message: Message, context: dict):
    request_id = context.pop("expert_reject_request_id", None)
    if request_id is None:
        await message.reply(MESSAGES["request_not_found"])
        return
    reason = message.content.strip()
    request = context["request_service"].reject_by_expert(request_id, reason)
    await context["bot"].send_message(
        request["seller_telegram_id"],
        f"{MESSAGES['expert_rejected_request']}\nدلیل: {reason}",
    )
    await message.reply(MESSAGES["request_rejected"])
    context.pop("state", None)


async def edit_seller_start(message: Message, context: dict):
    if get_role(message.author.id) != "expert":
        await message.reply(MESSAGES["not_allowed"])
        return
    user_service = context["user_service"]
    sellers = user_service.list_active_sellers_for_stores(expert_store_codes(message.author.id))
    if not sellers:
        await message.reply(MESSAGES["no_assigned_sellers"])
        return
    await message.reply(MESSAGES["select_seller_store"], components=seller_edit_keyboard(sellers))
    context["state"] = EDIT_SELLER_PICK


async def pick_seller_to_edit(callback: CallbackQuery, context: dict):
    seller_id = int(normalize_digits(callback.data.split(":", 1)[1]))
    user_service = context["user_service"]
    seller = user_service.get_user(seller_id)
    if not seller or seller["store_code"] not in expert_store_codes(callback.from_user.id):
        await callback.message.edit(MESSAGES["seller_not_for_expert"])
        return
    context["edit_seller_id"] = seller_id
    text = (
        f"{MESSAGES['seller_info']}\n"
        f"نام: {seller['full_name']}\n"
        f"موبایل: {seller['phone']}\n"
        f"کد فروشگاه: {seller['store_code']}"
    )
    await callback.message.edit(text, components=seller_edit_field_keyboard(seller_id))
    context["state"] = EDIT_SELLER_FIELD


async def pick_seller_field(callback: CallbackQuery, context: dict):
    action, seller_id_text = callback.data.rsplit(":", 1)
    context["edit_seller_id"] = int(normalize_digits(seller_id_text))
    if action == "edit_seller_name":
        await callback.message.edit(MESSAGES["ask_new_name"])
        context["state"] = EDIT_SELLER_NAME
    else:
        await callback.message.edit(MESSAGES["ask_new_phone"])
        context["state"] = EDIT_SELLER_PHONE


async def save_seller_name(message: Message, context: dict):
    seller_id = context.pop("edit_seller_id", None)
    if seller_id is None:
        await message.reply(MESSAGES["seller_not_for_expert"])
        return
    user_service = context["user_service"]
    seller = user_service.get_user(seller_id)
    if not seller or seller["store_code"] not in expert_store_codes(message.author.id):
        await message.reply(MESSAGES["seller_not_for_expert"])
        return
    user_service.update_seller_info(seller_id, full_name=message.content.strip())
    await message.reply(MESSAGES["seller_updated"])
    context.pop("state", None)


async def save_seller_phone(message: Message, context: dict):
    seller_id = context.pop("edit_seller_id", None)
    if seller_id is None:
        await message.reply(MESSAGES["seller_not_for_expert"])
        return
    phone = normalize_mobile(message.content)
    if not phone:
        await message.reply(MESSAGES["invalid_mobile"])
        context["state"] = EDIT_SELLER_PHONE
        return
    user_service = context["user_service"]
    seller = user_service.get_user(seller_id)
    if not seller or seller["store_code"] not in expert_store_codes(message.author.id):
        await message.reply(MESSAGES["seller_not_for_expert"])
        return
    user_service.update_seller_info(seller_id, phone=phone)
    await message.reply(MESSAGES["seller_updated"])
    context.pop("state", None)
