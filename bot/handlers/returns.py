from datetime import datetime
from pathlib import Path

from bale import CallbackQuery, Message

from bot.data.messages import MESSAGES
from bot.data.statuses import ACTIVE
from bot.services.return_service import ProductReturnError, RETURN_TYPE_LABELS_FA
from bot.utils.keyboards import (
    return_confirm_keyboard,
    return_products_keyboard,
    return_type_keyboard,
    seller_main_menu,
)
from bot.utils.normalize import normalize_digits
from data.static_data import get_role


RETURN_SELECT_PRODUCT, RETURN_TRACKING, RETURN_TYPE, RETURN_INVOICE, RETURN_SUMMARY = range(70, 75)
RETURN_PHOTO_DIR = Path("data/uploads/returns")


def _format_money(amount: int) -> str:
    return f"{int(amount):,}"


def _unit_for_tracking(context: dict, tracking: dict) -> tuple[dict | None, dict | None]:
    order = context["order_service"].get_order(tracking["order_id"])
    if not order:
        return None, None
    unit = next(
        (
            item
            for item in order.get("units", [])
            if int(item.get("index", 0)) == int(tracking["unit_index"])
        ),
        None,
    )
    return order, unit


def _commission_for_tracking(context: dict, tracking: dict) -> int:
    _order, unit = _unit_for_tracking(context, tracking)
    if not unit:
        return 0
    return int(unit.get("commission_amount") or 0)


def _summary(draft: dict) -> str:
    return MESSAGES["return_summary"].format(
        store_code=draft["store_code"],
        product_name=draft["product_name"],
        tracking_code=draft["tracking_code"],
        return_type=RETURN_TYPE_LABELS_FA[draft["return_type"]],
        commission_amount=_format_money(draft["commission_amount"]),
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
    draft["commission_amount"] = _commission_for_tracking(context, tracking)
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
        product_return = context["return_service"].create_return(seller, draft)
    except ProductReturnError:
        await callback.message.edit(MESSAGES["return_tracking_invalid"])
        return
    except ValueError:
        await callback.message.edit(MESSAGES["return_wallet_insufficient"])
        return

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
