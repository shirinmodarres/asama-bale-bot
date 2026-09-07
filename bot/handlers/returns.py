from datetime import datetime
from pathlib import Path

from bale import CallbackQuery, InputFile, Message

from bot.data.messages import MESSAGES
from bot.data.statuses import ACTIVE
from bot.services.return_service import ProductReturnError, RETURN_TYPE_LABELS_FA
from bot.utils.keyboards import (
    return_confirm_keyboard,
    return_products_keyboard,
    return_review_keyboard,
    return_type_keyboard,
    seller_main_menu,
)
from bot.utils.normalize import normalize_digits
from data.static_data import expert_store_codes, get_expert_for_store, get_role


RETURN_SELECT_PRODUCT, RETURN_TRACKING, RETURN_TYPE, RETURN_INVOICE, RETURN_SUMMARY, RETURN_REJECT_REASON = range(70, 76)
RETURN_PHOTO_DIR = Path("data/uploads/returns")


def _format_money(amount: int) -> str:
    return f"{int(amount):,}"


def _summary(draft: dict) -> str:
    return MESSAGES["return_summary"].format(
        store_code=draft["store_code"],
        product_name=draft["product_name"],
        tracking_code=draft["tracking_code"],
        return_type=RETURN_TYPE_LABELS_FA[draft["return_type"]],
    )


def _return_review_text(product_return: dict) -> str:
    return MESSAGES["return_for_expert_review"].format(
        return_id=product_return["return_id"],
        store_code=product_return["store_code"],
        product_name=product_return["product_name"],
        tracking_code=product_return["tracking_code"],
        return_type=RETURN_TYPE_LABELS_FA.get(product_return["return_type"], product_return["return_type"]),
    )


async def _save_return_invoice_photo(message: Message, context: dict) -> str:
    photo = message.photos[-1]
    RETURN_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{message.author.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{photo.file_unique_id}.jpg"
    path = RETURN_PHOTO_DIR / filename
    bale_file = await context["bot"].get_file(photo.file_id)
    if hasattr(bale_file, "download_to_drive"):
        await bale_file.download_to_drive(path)
    elif isinstance(bale_file, (bytes, bytearray)):
        path.write_bytes(bale_file)
    else:
        path.write_bytes(bytes(bale_file))
    return str(path)


async def return_start(message: Message, context: dict):
    if get_role(message.author.id) is not None:
        await message.reply(MESSAGES["return_start_not_seller"])
        return
    seller = context["user_service"].get_user(message.author.id)
    if not seller or seller.get("status") != ACTIVE:
        await message.reply(MESSAGES["return_start_not_seller"])
        return

    products = context["return_service"].list_returnable_products_for_seller(seller)
    if not products:
        await message.reply(MESSAGES["return_no_sold_items"], components=seller_main_menu())
        return

    context["return_seller"] = seller
    context["return_products"] = products
    await message.reply(MESSAGES["return_select_item"], components=return_products_keyboard(products))
    context["state"] = RETURN_SELECT_PRODUCT


async def choose_return_product(callback: CallbackQuery, context: dict):
    seller = context.get("return_seller") or context["user_service"].get_user(callback.from_user.id)
    if not seller or seller.get("status") != ACTIVE:
        await callback.message.edit(MESSAGES["return_start_not_seller"])
        context.pop("state", None)
        return
    product_key = callback.data.split(":", 1)[1]
    products = context.get("return_products") or context["return_service"].list_returnable_products_for_seller(seller)
    product = next(
        (
            item
            for item in products
            if (item.get("product_key") or item.get("product_code", "")) == product_key
        ),
        None,
    )
    if not product:
        await callback.message.edit(MESSAGES["return_tracking_invalid"])
        context.pop("state", None)
        return
    context["return_seller"] = seller
    context["return_draft"] = {
        "store_code": seller["store_code"],
        "product_name": product.get("product_name", ""),
        "product_key": product.get("product_key", ""),
        "product_code": product.get("product_code", ""),
        "quantity": 1,
    }
    await callback.message.edit(MESSAGES["return_ask_tracking"])
    context["state"] = RETURN_TRACKING


async def receive_return_tracking(message: Message, context: dict):
    tracking_code = normalize_digits(message.content or "")
    draft = context.get("return_draft")
    seller = context.get("return_seller")
    if not draft or not seller:
        await message.reply(MESSAGES["return_tracking_invalid"])
        context.pop("state", None)
        return
    sold_tracking = context["return_service"].get_sold_tracking_for_seller(seller, tracking_code)
    if not sold_tracking:
        await message.reply(MESSAGES["return_tracking_invalid"])
        return
    tracking = context["return_service"].get_sold_tracking_for_seller_product(
        seller,
        tracking_code,
        draft.get("product_key", ""),
        draft.get("product_code", ""),
    )
    if not tracking:
        await message.reply(MESSAGES["return_tracking_mismatch"])
        return
    draft["tracking_code"] = tracking_code
    await message.reply(MESSAGES["return_select_type"], components=return_type_keyboard())
    context["state"] = RETURN_TYPE


async def choose_return_type(callback: CallbackQuery, context: dict):
    return_type = callback.data.split(":", 1)[1]
    context["return_draft"]["return_type"] = return_type
    await callback.message.edit(MESSAGES["return_ask_invoice_photo"])
    context["state"] = RETURN_INVOICE


async def receive_return_invoice(message: Message, context: dict):
    if not message.photos:
        await message.reply(MESSAGES["return_invoice_photo_required"])
        return
    context["return_draft"]["invoice_image_path"] = await _save_return_invoice_photo(message, context)
    await message.reply(_summary(context["return_draft"]), components=return_confirm_keyboard())
    context["state"] = RETURN_SUMMARY


async def confirm_return(callback: CallbackQuery, context: dict):
    seller = context.get("return_seller")
    draft = context.get("return_draft")
    if not seller or not draft:
        await callback.message.edit(MESSAGES["return_tracking_invalid"])
        context.pop("state", None)
        return
    try:
        product_return = context["return_service"].create_return_request(seller, draft)
    except ProductReturnError:
        await callback.message.edit(MESSAGES["return_tracking_invalid"])
        return

    expert = get_expert_for_store(product_return["store_code"])
    if expert:
        await context["bot"].send_message(
            expert["telegram_id"],
            _return_review_text(product_return),
            components=return_review_keyboard(product_return["return_id"]),
        )
        invoice_path = Path(product_return.get("invoice_image_path", ""))
        if invoice_path.is_file():
            with invoice_path.open("rb") as file:
                await context["bot"].send_photo(
                    expert["telegram_id"],
                    InputFile(file.read(), file_name=invoice_path.name),
                    caption=f"فاکتور مرجوعی {product_return['return_id']}",
                )

    context.pop("return_seller", None)
    context.pop("return_draft", None)
    context.pop("return_products", None)
    context.pop("state", None)
    await callback.message.edit(MESSAGES["return_registered"].format(return_id=product_return["return_id"]))


async def cancel_return(message: Message, context: dict):
    context.pop("return_seller", None)
    context.pop("return_draft", None)
    context.pop("return_products", None)
    context.pop("state", None)
    await message.reply(MESSAGES["return_cancelled"], components=seller_main_menu())


async def cancel_return_callback(callback: CallbackQuery, context: dict):
    context.pop("return_seller", None)
    context.pop("return_draft", None)
    context.pop("return_products", None)
    context.pop("state", None)
    await callback.message.edit(MESSAGES["return_cancelled"])


async def pending_returns(message: Message, context: dict):
    if get_role(message.author.id) != "expert":
        await message.reply(MESSAGES["not_allowed"])
        return
    returns = context["return_service"].list_pending_for_stores(expert_store_codes(message.author.id))
    if not returns:
        await message.reply(MESSAGES["return_no_pending"])
        return
    await message.reply(MESSAGES["return_pending_list"])
    for product_return in returns:
        await message.reply(
            _return_review_text(product_return),
            components=return_review_keyboard(product_return["return_id"]),
        )


async def return_review_callback(callback: CallbackQuery, context: dict):
    if get_role(callback.from_user.id) != "expert":
        await callback.message.edit(MESSAGES["not_allowed"])
        return
    _prefix, action, return_id = callback.data.split(":", 2)
    product_return = context["return_service"].get_return(return_id)
    if not product_return or product_return["store_code"] not in expert_store_codes(callback.from_user.id):
        await callback.message.edit(MESSAGES["return_not_for_expert"])
        return
    if product_return.get("status") != "pending":
        await callback.message.edit(MESSAGES["return_already_reviewed"])
        return

    if action == "reject":
        context["return_review_id"] = return_id
        context["state"] = RETURN_REJECT_REASON
        await callback.message.edit(MESSAGES["return_ask_reject_reason"])
        return

    try:
        approved = context["return_service"].approve_return(return_id, callback.from_user.id)
    except ValueError:
        await callback.message.edit(MESSAGES["return_wallet_insufficient"])
        return
    except Exception:
        await callback.message.edit(MESSAGES["return_tracking_invalid"])
        return

    performance = approved.get("commission_performance")
    commission_message = context["commission_service"].build_realtime_message(performance)
    seller_message = MESSAGES["return_approved_seller"].format(return_id=approved["return_id"])
    if commission_message:
        seller_message = f"{seller_message}\n\n{commission_message}"
    await context["bot"].send_message(approved["seller_telegram_id"], seller_message)
    await callback.message.edit(MESSAGES["return_approved_expert"].format(return_id=approved["return_id"]))


async def receive_return_reject_reason(message: Message, context: dict):
    if get_role(message.author.id) != "expert":
        await message.reply(MESSAGES["not_allowed"])
        context.pop("state", None)
        return
    return_id = context.pop("return_review_id", None)
    if not return_id:
        await message.reply(MESSAGES["return_already_reviewed"])
        context.pop("state", None)
        return
    reason = (message.content or "").strip()
    try:
        product_return = context["return_service"].reject_return(return_id, message.author.id, reason)
    except ProductReturnError:
        await message.reply(MESSAGES["return_already_reviewed"])
        context.pop("state", None)
        return
    await context["bot"].send_message(
        product_return["seller_telegram_id"],
        MESSAGES["return_rejected_seller"].format(return_id=return_id, reason=reason),
    )
    await message.reply(MESSAGES["return_rejected_expert"].format(return_id=return_id))
    context.pop("state", None)
