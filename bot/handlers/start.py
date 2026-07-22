from bale import Message

from bot.data.messages import MESSAGES
from bot.services.notification_service import notify_seller_approval
from bot.data.statuses import ACTIVE, PENDING_SELLER_APPROVAL, SELLER_REJECTED
from bot.utils.keyboards import admin_menu, expert_menu, sales_manager_menu, seller_main_menu
from bot.utils.normalize import normalize_digits
from bot.utils.validators import normalize_mobile
from data.static_data import get_expert_for_store, get_role, get_store

STORE_CODE, FULL_NAME, PHONE = range(1, 4)


async def start(message: Message, context: dict):
    telegram_id = message.author.id
    role = get_role(telegram_id)
    if role == "admin":
        await message.reply(MESSAGES["admin_start"], components=admin_menu())
        context.pop("state", None)
        return
    if role == "sales_manager":
        await message.reply(MESSAGES["sales_manager_start"], components=sales_manager_menu())
        context.pop("state", None)
        return
    if role == "expert":
        await message.reply(MESSAGES["expert_start"], components=expert_menu())
        context.pop("state", None)
        return

    user_service = context["user_service"]
    user = user_service.get_user(telegram_id)
    if user and user["status"] == ACTIVE:
        await message.reply(MESSAGES["seller_welcome"], components=seller_main_menu())
        context.pop("state", None)
        return
    if user and user["status"] == PENDING_SELLER_APPROVAL:
        await message.reply(MESSAGES["seller_waiting"])
        context.pop("state", None)
        return
    if user and user["status"] == SELLER_REJECTED:
        await message.reply(MESSAGES["seller_rejected"])
        context.pop("state", None)
        return

    await message.reply(MESSAGES["ask_store_code"])
    context["state"] = STORE_CODE


async def receive_store_code(message: Message, context: dict):
    if context.get("state") != STORE_CODE:
        await message.reply("لطفاً ابتدا دستور /start را بزنید.")
        return

    user_service = context["user_service"]
    code = normalize_digits(message.content)
    store = get_store(code)
    if not store:
        await message.reply(MESSAGES["invalid_store_code"])
        return

    approved_seller = user_service.get_approved_seller_by_store(code)
    if approved_seller and approved_seller["telegram_id"] != message.author.id:
        await message.reply(MESSAGES["store_has_seller"])
        context.pop("state", None)
        return

    expert = get_expert_for_store(code)
    if not expert:
        await message.reply(MESSAGES["store_has_no_expert"])
        context.pop("state", None)
        return

    context["store_code"] = code
    await message.reply(MESSAGES["ask_full_name"])
    context["state"] = FULL_NAME


async def receive_full_name(message: Message, context: dict):
    if context.get("state") != FULL_NAME:
        await message.reply("لطفاً ابتدا دستور /start را بزنید.")
        return
    context["full_name"] = message.content.strip()
    await message.reply(MESSAGES["ask_phone"])
    context["state"] = PHONE


async def receive_phone(message: Message, context: dict):
    if context.get("state") != PHONE:
        await message.reply("لطفاً ابتدا دستور /start را بزنید.")
        return

    user_service = context["user_service"]
    phone = normalize_mobile(message.content)
    if not phone:
        await message.reply(MESSAGES["invalid_mobile"])
        return

    store_code = context["store_code"]
    seller = user_service.save_pending_seller(
        telegram_id=message.author.id,
        store_code=store_code,
        full_name=context["full_name"],
        phone=phone,
    )
    await notify_seller_approval(context, get_expert_for_store(store_code), seller, store_code)
    context.pop("state", None)
    context.pop("store_code", None)
    context.pop("full_name", None)
    await message.reply(MESSAGES["seller_pending"])