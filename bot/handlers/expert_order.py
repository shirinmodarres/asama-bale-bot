import logging
from bale import Message, CallbackQuery, InputFile
from datetime import datetime
from pathlib import Path

from bot.data.messages import MESSAGES, VALIDATION_REJECTION_REASONS
from bot.data.statuses import ACTIVE, order_status_label
from bot.services.user_service import COMMISSION_PERCENT, calculate_commission
from bot.utils.keyboards import (
    BTN_CANCEL,
    categories_keyboard,
    order_unit_validation_keyboard,
    order_rejection_reasons_keyboard,
    order_unit_field_keyboard,
    order_units_keyboard,
    order_validation_inline_keyboard,
    order_text_navigation_menu,
    products_keyboard,
    seller_main_menu,
)
from bot.utils.normalize import normalize_digits
from data.static_data import CATEGORIES, STORES, expert_store_codes, get_expert_for_store, get_role

logger = logging.getLogger(__name__)

# ====== Stateهای مستقل برای ثبت سریال ======
ORDER_CATEGORY, ORDER_PRODUCT, ORDER_QUANTITY, ORDER_TRACKING, ORDER_FACTOR, ORDER_SUMMARY, ORDER_REJECT_REASON, ORDER_CUSTOM_REJECT_REASON, ORDER_EDIT, ORDER_EDIT_FIELD = range(30, 40)

ORDER_PHOTO_DIR = Path("data/uploads/orders")


# ====== توابع کمکی ======
async def _save_photo(message: Message, context: dict, kind: str) -> dict:
    logger.info("receive_order_factor: _save_photo entered for kind=%s author=%s", kind, message.author.id)
    if not getattr(message, 'photos', None):
        logger.warning("_save_photo: no photos on message from %s", message.author.id)
        return {"type": "text", "value": "عکس دریافت نشد", "file_id": None}
    photo = message.photos[-1]
    ORDER_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{message.author.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{kind}_{photo.file_unique_id}.jpg"
    path = ORDER_PHOTO_DIR / filename
    bale_file = await context["bot"].get_file(photo.file_id)
    try:
        # Some Bale versions return a File-like object with a download method,
        # older/newer versions may return raw bytes. Support both.
        if hasattr(bale_file, "download_to_drive"):
            await bale_file.download_to_drive(path)
        elif isinstance(bale_file, (bytes, bytearray)):
            path.write_bytes(bale_file)
        else:
            # Fallback: try converting to bytes
            try:
                data = bytes(bale_file)
                path.write_bytes(data)
            except Exception:
                logger.exception("_save_photo: unexpected get_file() return type: %s", type(bale_file))
                return {"type": "text", "value": "عکس دریافت نشد", "file_id": photo.file_id}
    except Exception as exc:
        logger.exception("_save_photo: error saving file: %s", exc)
        return {"type": "text", "value": "عکس دریافت نشد", "file_id": photo.file_id}
    logger.info("_save_photo: saved photo to %s (file_id=%s)", path, photo.file_id)
    return {"type": "photo", "value": None, "file_id": photo.file_id, "local_path": str(path)}


async def _media_value(message: Message, context: dict, kind: str):
    if message.photos:
        return await _save_photo(message, context, kind)
    return {"type": "text", "value": normalize_digits(message.content or ""), "file_id": None}


def _format_media(value: dict) -> str:
    if value["type"] == "photo":
        return MESSAGES["order_photo_label"]
    return value.get("value") or "-"


def _summary(draft_or_order: dict) -> str:
    seller_name = draft_or_order.get("seller_name", "-")
    lines = [
        MESSAGES["order_summary"],
        MESSAGES["order_summary_store"].format(
            store_code=draft_or_order["store_code"],
            store_name=draft_or_order["store_name"],
        ),
        MESSAGES["order_summary_seller"].format(seller_name=seller_name),
        MESSAGES["order_summary_product"].format(
            category_name=draft_or_order["category_name"],
            product_name=draft_or_order["product_name"],
            product_model=draft_or_order["product_model"],
        ),
        MESSAGES["order_summary_quantity"].format(quantity=draft_or_order["quantity"]),
        "",
        MESSAGES["order_registered_info"],
    ]
    for unit in draft_or_order.get("units", []):
        lines.append(MESSAGES["order_summary_unit"].format(
            index=unit["index"],
            tracking=_format_media(unit["tracking_code"]),
            factor=_format_media(unit.get("factor_image") or {"type": "text", "value": "-", "file_id": None}),
        ))
    return "\n".join(lines)


def _unit_status_label(status: str) -> str:
    return {"pending": "در انتظار بررسی", "approved": "تایید شده", "rejected": "رد شده"}.get(status, status)


def _format_money(amount: int) -> str:
    return f"{amount:,}"


def _unit_approved_expert_text(order: dict, unit: dict) -> str:
    """متن نهایی پیام کارشناس بعد از تأیید اعتبارسنجی یک کالا."""
    tracking_value = _format_media(unit.get("tracking_code") or {"type": "text", "value": "-", "file_id": None})
    lines = [
        "✅ کالای سفارش با موفقیت تأیید شد",
        "",
        MESSAGES["order_summary_seller"].format(seller_name=order.get("seller_name", "-")),
        MESSAGES["order_summary_product"].format(
            category_name=order["category_name"],
            product_name=order["product_name"],
            product_model=order["product_model"],
        ),
        f"کد رهگیری: {tracking_value}",
        f"سفارش: {order['id']} | کالای شماره {unit['index']}",
        f"وضعیت سفارش: {order_status_label(order['status'])}",
    ]
    return "\n".join(lines)


def _unit_rejected_expert_text(order: dict, unit: dict) -> str:
    tracking_value = _format_media(unit.get("tracking_code") or {"type": "text", "value": "-", "file_id": None})
    lines = [
        "❌ کالای سفارش رد شد",
        "",
        MESSAGES["order_summary_seller"].format(seller_name=order.get("seller_name", "-")),
        MESSAGES["order_summary_product"].format(
            category_name=order["category_name"],
            product_name=order["product_name"],
            product_model=order["product_model"],
        ),
        f"کد رهگیری: {tracking_value}",
        f"سفارش: {order['id']} | کالای شماره {unit['index']}",
        f"وضعیت سفارش: {order_status_label(order['status'])}",
    ]
    if unit.get("rejection_reason_text"):
        lines.append(f"علت رد: {unit['rejection_reason_text']}")
    return "\n".join(lines)


async def _finalize_expert_message(context: dict, message: Message, text: str, expert_id: int | None = None) -> None:
    """Remove the old validation message/buttons and send a clean final result.

    python-bale-bot only sends reply_markup when components is truthy, so
    edit(..., components=None) does not reliably remove inline buttons.
    """
    try:
        await message.delete()
    except Exception:
        logger.exception("_finalize_expert_message: حذف پیام قبلی کارشناس ناموفق بود")
    target_id = expert_id or getattr(message, "chat_id", None)
    if target_id:
        try:
            await context["bot"].send_message(target_id, text)
            return
        except Exception:
            logger.exception("_finalize_expert_message: ارسال پیام نهایی به کارشناس ناموفق بود")
    try:
        await message.reply(text)
    except Exception:
        logger.exception("_finalize_expert_message: reply پیام نهایی به کارشناس ناموفق بود")


def _unit_summary(order: dict, unit: dict) -> str:
    lines = [
        MESSAGES["order_unit_for_expert_validation"].format(index=unit["index"], order_id=order["id"]),
        MESSAGES["order_summary_store"].format(store_code=order["store_code"], store_name=order["store_name"]),
        MESSAGES["order_summary_seller"].format(seller_name=order.get("seller_name", "-")),
        MESSAGES["order_summary_product"].format(
            category_name=order["category_name"],
            product_name=order["product_name"],
            product_model=order["product_model"],
        ),
        f"وضعیت کالا: {_unit_status_label(unit.get('validation_status', 'pending'))}",
        MESSAGES["order_summary_unit"].format(
            index=unit["index"],
            tracking=_format_media(unit["tracking_code"]),
            factor=_format_media(unit.get("factor_image") or {"type": "text", "value": "-", "file_id": None}),
        ),
    ]
    if unit.get("rejection_reason_text"):
        lines.append(f"علت رد: {unit['rejection_reason_text']}")
    return "\n".join(lines)


def _photo_input_file(photo: dict) -> InputFile | None:
    """Build the InputFile required by python-bale-bot 2.5."""
    local_path = photo.get("local_path")
    if local_path:
        path = Path(local_path)
        if path.is_file():
            return InputFile(path.read_bytes(), file_name=path.name)
    file_id = photo.get("file_id")
    if file_id:
        return InputFile(file_id)
    return None


async def _send_order_units_to_expert(context: dict, order: dict) -> None:
    expert_id = order.get("expert_telegram_id")
    logger.info(f"🔍 expert_id: {expert_id}")
    if not expert_id:
        logger.error("❌ expert_telegram_id در سفارش وجود ندارد!")
        return

    logger.info("🔍 ارسال پیام خلاصه به کارشناس")
    await context["bot"].send_message(
        expert_id,
        f"{MESSAGES['order_for_expert_validation']}\n\n{_summary(order)}",
    )

    for unit in order.get("units", []):
        if unit.get("validation_status", "pending") != "pending":
            continue
        logger.info(f"🔍 ارسال جزئیات واحد {unit['index']} به کارشناس")
        tracking = unit.get("tracking_code", {})
        tracking_file = _photo_input_file(tracking)
        if tracking.get("type") == "photo" and tracking_file:
            await context["bot"].send_photo(
                expert_id,
                tracking_file,
                caption=MESSAGES["order_tracking_photo_caption"].format(
                    order_id=order["id"],
                    index=unit["index"],
                    total=order["quantity"],
                ),
            )
        factor = unit.get("factor_image", {})
        factor_file = _photo_input_file(factor)
        if factor.get("type") == "photo" and factor_file:
            logger.info(f"🔍 ارسال عکس فاکتور واحد {unit['index']}")
            await context["bot"].send_photo(
                expert_id,
                factor_file,
                caption=_unit_summary(order, unit),
                components=order_unit_validation_keyboard(order["id"], unit["index"]),
            )
        else:
            await context["bot"].send_message(
                expert_id,
                _unit_summary(order, unit),
                components=order_unit_validation_keyboard(order["id"], unit["index"]),
            )
    logger.info("✅ تمام پیام‌ها و عکس‌ها ارسال شدند.")


def _expert_for_store(store_code: str) -> dict:
    return get_expert_for_store(store_code)


# ====== ورود به جریان ثبت سریال ======
async def order_start(message: Message, context: dict):
    if get_role(message.author.id) is not None:
        await message.reply(MESSAGES["order_start_not_seller"])
        return
    seller = context["user_service"].get_user(message.author.id)
    if not seller or seller.get("status") != ACTIVE:
        await message.reply(MESSAGES["order_start_not_seller"])
        return
    store = STORES.get(seller["store_code"])
    if not store:
        await message.reply(MESSAGES["order_no_store"])
        return
    expert = _expert_for_store(seller["store_code"])
    if not expert:
        await message.reply(MESSAGES["store_has_no_expert"])
        return
    context["order_draft"] = {
        "store_code": seller["store_code"],
        "store_name": store["name"],
        "seller_telegram_id": seller["telegram_id"],
        "seller_name": seller["full_name"],
        "seller_phone": seller["phone"],
        "expert_telegram_id": expert["telegram_id"],
        "expert_name": expert["full_name"],
    }
    await message.reply(MESSAGES["choose_category"], components=categories_keyboard(navigation_prefix="order"))
    context["state"] = ORDER_CATEGORY


# ====== انتخاب دسته‌بندی ======
async def choose_order_category(callback: CallbackQuery, context: dict):
    category_key = callback.data.split(":", 1)[1]
    draft = context["order_draft"]
    draft["category_key"] = category_key
    draft["category_name"] = CATEGORIES[category_key]["name"]
    await callback.message.edit(MESSAGES["choose_product"], components=products_keyboard(category_key, navigation_prefix="order"))
    context["state"] = ORDER_PRODUCT


# ====== انتخاب محصول ======
async def choose_order_product(callback: CallbackQuery, context: dict):
    product_key = callback.data.split(":", 1)[1]
    draft = context["order_draft"]
    product = CATEGORIES[draft["category_key"]]["products"][product_key]
    draft["product_key"] = product_key
    draft["product_name"] = product["name"]
    draft["product_model"] = product["model"]
    draft["product_price"] = product.get("price", 0)
    await callback.message.edit(
        f"{MESSAGES['order_selected_product']}\n{product['name']}\n\n{MESSAGES['order_ask_quantity']}",
        components=order_text_navigation_menu(),
    )
    context["state"] = ORDER_QUANTITY


# ====== دریافت تعداد ======
async def receive_order_quantity(message: Message, context: dict):
    if message.photos:
        await message.reply(MESSAGES["order_quantity_required"])
        return
    text = normalize_digits(message.content)
    if not text.isdigit() or int(text) <= 0:
        await message.reply(MESSAGES["invalid_quantity"])
        return
    draft = context["order_draft"]
    draft["quantity"] = int(text)
    draft["units"] = []
    context["order_unit_index"] = 1
    await message.reply(
        MESSAGES["order_ask_tracking"].format(index=1, total=draft["quantity"]),
        components=order_text_navigation_menu(),
    )
    context["state"] = ORDER_TRACKING


# ====== دریافت کد رهگیری ======
async def receive_order_tracking(message: Message, context: dict):
    if not message.photos and not message.content:
        await message.reply(MESSAGES["order_tracking_required"], components=order_text_navigation_menu())
        return
    draft = context["order_draft"]
    if "edit_unit_index" in context:
        unit = draft["units"][context.pop("edit_unit_index") - 1]
        unit["tracking_code"] = await _media_value(message, context, "tracking")
        await message.reply(_summary(draft), components=order_validation_inline_keyboard())
        context["state"] = ORDER_SUMMARY
        return
    index = context["order_unit_index"]
    context["pending_unit_tracking"] = await _media_value(message, context, "tracking")
    await message.reply(
        MESSAGES["order_ask_factor"].format(index=index, total=draft["quantity"]),
        components=order_text_navigation_menu(),
    )
    context["state"] = ORDER_FACTOR


# ====== دریافت عکس فاکتور ======
async def receive_order_factor(message: Message, context: dict):
    logger.info("receive_order_factor entered for user=%s state=%s", message.author.id, context.get('state'))
    # فقط عکس قبول می‌شود
    if not getattr(message, 'photos', None):
        logger.info("receive_order_factor: no photos present")
        await message.reply(MESSAGES["order_factor_photo_required"])
        return

    draft = context["order_draft"]
    if "edit_unit_index" in context:
        unit = draft["units"][context.pop("edit_unit_index") - 1]
        unit["factor_image"] = await _save_photo(message, context, "factor")
        logger.info("receive_order_factor: edited unit %s factor saved", unit['index'])
        await message.reply(_summary(draft), components=order_validation_inline_keyboard())
        context["state"] = ORDER_SUMMARY
        return

    index = context["order_unit_index"]
    factor = await _save_photo(message, context, "factor")
    draft["units"].append({
        "index": index,
        "tracking_code": context.pop("pending_unit_tracking"),
        "factor_image": factor,
        "validation_status": "pending",
        "rejection_reason_key": None,
        "rejection_reason_text": None,
    })
    logger.info("receive_order_factor: appended unit %s factor_file=%s", index, factor.get('file_id'))
    if index < draft["quantity"]:
        context["order_unit_index"] = index + 1
        await message.reply(
            MESSAGES["order_ask_tracking"].format(index=index + 1, total=draft["quantity"]),
            components=order_text_navigation_menu(),
        )
        context["state"] = ORDER_TRACKING
        return
    context.pop("order_unit_index", None)
    await message.reply(_summary(draft), components=order_validation_inline_keyboard())
    context["state"] = ORDER_SUMMARY


# ====== ثبت نهایی سفارش ======
async def submit_order(message: Message, context: dict):
    logger.info("🔍 submit_order فراخوانی شد. user=%s", message.author.id)
    draft = context.get("order_draft")
    if not draft:
        logger.error("❌ order_draft در context وجود ندارد!")
        await message.reply(MESSAGES["order_under_expert_review"])
        return

    logger.info(f"📦 draft: {draft}")
    order_service = context["order_service"]
    logger.info("🔍 قبل از create_order")
    order = order_service.create_order(draft)
    logger.info(f"✅ سفارش ایجاد شد: {order.get('id')}")
    context.pop("order_draft", None)
    # ensure we clear state explicitly
    context.pop("state", None)
    logger.info("🔍 قبل از _send_order_units_to_expert")
    await _send_order_units_to_expert(context, order)
    logger.info("✅ _send_order_units_to_expert اجرا شد.")
    await message.reply(f"{MESSAGES['order_submitted']}\n{order['id']}", components=seller_main_menu())
    logger.info("submit_order finished: order_id=%s sent to expert=%s", order.get('id'), order.get('expert_telegram_id'))


# ====== ویرایش اطلاعات کالاها ======
async def edit_order_menu(message: Message, context: dict):
    await message.reply(
        MESSAGES["order_edit_menu"],
        components=order_units_keyboard(context["order_draft"].get("units", [])),
    )
    context["state"] = ORDER_EDIT


async def choose_order_edit_unit(callback: CallbackQuery, context: dict):
    unit_index = int(normalize_digits(callback.data.split(":", 1)[1]))
    context["edit_unit_index"] = unit_index
    await callback.message.edit(MESSAGES["order_edit_field"], components=order_unit_field_keyboard(unit_index))
    context["state"] = ORDER_EDIT_FIELD


async def choose_order_edit_field(callback: CallbackQuery, context: dict):
    field, unit_index = callback.data.rsplit(":", 1)
    context["edit_unit_index"] = int(normalize_digits(unit_index))
    draft = context["order_draft"]
    if field == "order_edit_tracking":
        await callback.message.edit(
            MESSAGES["order_ask_tracking"].format(index=context["edit_unit_index"], total=draft["quantity"])
        )
        context["state"] = ORDER_TRACKING
    else:
        await callback.message.edit(
            MESSAGES["order_ask_factor"].format(index=context["edit_unit_index"], total=draft["quantity"])
        )
        context["state"] = ORDER_FACTOR


# ====== لغو سفارش ======
async def cancel_order(message: Message, context: dict):
    context.pop("order_draft", None)
    context.pop("state", None)
    await message.reply(MESSAGES["order_cancelled"], components=seller_main_menu())


async def back_order(message: Message, context: dict):
    """Move one safe step back without submitting the serial order."""
    state = context.get("state")
    draft = context.get("order_draft")
    if not draft or state == ORDER_CATEGORY:
        await cancel_order(message, context)
        return
    if state == ORDER_PRODUCT:
        await message.reply(MESSAGES["choose_category"], components=categories_keyboard(navigation_prefix="order"))
        context["state"] = ORDER_CATEGORY
        return
    if state == ORDER_QUANTITY:
        await message.reply(
            MESSAGES["choose_product"],
            components=products_keyboard(draft["category_key"], navigation_prefix="order"),
        )
        context["state"] = ORDER_PRODUCT
        return
    if state == ORDER_FACTOR:
        if "edit_unit_index" in context:
            context.pop("edit_unit_index", None)
            await edit_order_menu(message, context)
            return
        context.pop("pending_unit_tracking", None)
        index = context.get("order_unit_index", 1)
        await message.reply(
            MESSAGES["order_ask_tracking"].format(index=index, total=draft.get("quantity", 1)),
            components=order_text_navigation_menu(),
        )
        context["state"] = ORDER_TRACKING
        return
    if state == ORDER_TRACKING:
        if "edit_unit_index" in context:
            context.pop("edit_unit_index", None)
            await edit_order_menu(message, context)
            return
        draft.pop("quantity", None)
        draft.pop("units", None)
        context.pop("order_unit_index", None)
        await message.reply(MESSAGES["order_ask_quantity"], components=order_text_navigation_menu())
        context["state"] = ORDER_QUANTITY
        return
    if state == ORDER_SUMMARY:
        await edit_order_menu(message, context)
        return
    if state == ORDER_EDIT_FIELD:
        context.pop("edit_unit_index", None)
        await edit_order_menu(message, context)
        return
    await message.reply(_summary(draft), components=order_validation_inline_keyboard())
    context["state"] = ORDER_SUMMARY


# ====== دکمه‌های Inline خلاصه‌ی سفارش (ثبت نهایی / ویرایش / لغو) ======
# نکته: این تابع قبلاً اصلاً وجود نداشت. بعد از نمایش خلاصه با
# order_validation_inline_keyboard()، callback_data به‌شکل "order_submit:confirm"،
# "order_submit:edit" یا "order_submit:cancel" برای بات می‌آید ولی هیچ‌جا روت
# نشده بود - برای همین با تپ روی «ثبت نهایی» هیچ اتفاقی نمی‌افتاد.
# submit_order/edit_order_menu/cancel_order فقط از message.reply استفاده
# می‌کنند (نه message.author)، پس دادن callback.message به آن‌ها به‌جای یک
# Message واقعی کاملاً کار می‌کند.
async def order_submit_callback(callback: CallbackQuery, context: dict):
    _prefix, action = callback.data.split(":", 1)
    if action == "confirm":
        await submit_order(callback.message, context)
        return
    if action == "edit":
        await edit_order_menu(callback.message, context)
        return
    if action == "cancel":
        await cancel_order(callback.message, context)
        return


# ====== مشاهده سفارش‌های در انتظار کارشناس ======
async def pending_orders(message: Message, context: dict):
    if get_role(message.author.id) != "expert":
        await message.reply(MESSAGES["not_allowed"])
        return
    orders = context["order_service"].list_pending_for_stores(
        expert_store_codes(message.author.id)
    )
    if not orders:
        await message.reply(MESSAGES["order_no_pending"])
        return
    await message.reply(MESSAGES["order_pending_list"])
    for order in orders:
        await message.reply(_summary(order))
        for unit in order.get("units", []):
            if unit.get("validation_status", "pending") != "pending":
                continue
            factor = unit.get("factor_image", {})
            tracking = unit.get("tracking_code", {})
            tracking_file = _photo_input_file(tracking)
            if tracking.get("type") == "photo" and tracking_file:
                await context["bot"].send_photo(
                    message.author.id,
                    tracking_file,
                    caption=MESSAGES["order_tracking_photo_caption"].format(
                        order_id=order["id"],
                        index=unit["index"],
                        total=order["quantity"],
                    ),
                )
            factor_file = _photo_input_file(factor)
            if factor.get("type") == "photo" and factor_file:
                await context["bot"].send_photo(
                    message.author.id,
                    factor_file,
                    caption=_unit_summary(order, unit),
                    components=order_unit_validation_keyboard(order["id"], unit["index"]),
                )
            else:
                await message.reply(
                    _unit_summary(order, unit),
                    components=order_unit_validation_keyboard(order["id"], unit["index"]),
                )


# ====== اعتبارسنجی توسط کارشناس ======
async def order_validation_callback(callback: CallbackQuery, context: dict):
    if get_role(callback.from_user.id) != "expert":
        await callback.message.edit(MESSAGES["not_allowed"])
        return
    _prefix, action, order_id, unit_index_text = callback.data.split(":", 3)
    unit_index = int(normalize_digits(unit_index_text))
    order = context["order_service"].get_order(order_id)
    if not order or order["store_code"] not in expert_store_codes(callback.from_user.id):
        await callback.message.edit(MESSAGES["order_not_for_expert"])
        return
    unit = next((item for item in order.get("units", []) if int(item["index"]) == unit_index), None)
    if not unit:
        await callback.message.edit(MESSAGES["order_not_for_expert"])
        return
    if unit.get("validation_status", "pending") != "pending":
        await callback.message.reply(MESSAGES["order_unit_already_reviewed"])
        return

    if action == "approve":
        # مرحله‌ی ۱: عملیات واقعی در دیتابیس. اگر اینجا خطا بدهد، هیچ پیامی به
        # فروشنده ارسال نمی‌شود و پیام/دکمه‌های کارشناس هم دست‌نخورده باقی
        # می‌مانند (یعنی می‌تواند دوباره تلاش کند)، فقط یک خطای مناسب نشان داده می‌شود.
        try:
            order = context["order_service"].approve_unit_validation(order_id, unit_index)
        except Exception:
            logger.exception(
                "order_validation_callback: تایید سریال order_id=%s unit_index=%s در دیتابیس ناموفق بود",
                order_id, unit_index,
            )
            await callback.message.reply(
                MESSAGES.get("order_unit_approve_failed", "❌ تایید سریال با خطا مواجه شد. لطفاً دوباره تلاش کنید.")
            )
            return

        # مرحله‌ی ۲: DB با موفقیت آپدیت شد؛ حالا محاسبه‌ی کمیسیون و اطلاع به فروشنده.
        commission = calculate_commission(order.get("product_price", 0))
        transaction_id = f"wallet:{order['id']}:{unit_index}"
        wallet, credited = context["user_service"].credit_wallet(
            order["seller_telegram_id"],
            commission,
            transaction_id=transaction_id,
            description=f"شارژ بابت تایید فاکتور سفارش {order['id']} کالای {unit_index}",
        )
        order = context["order_service"].save_unit_commission(
            order["id"],
            unit_index,
            COMMISSION_PERCENT,
            commission,
            transaction_id,
        ) or order
        await context["bot"].send_message(
            order["seller_telegram_id"],
            MESSAGES["order_unit_approved_notify"].format(index=unit_index, order_id=order["id"]),
        )
        if credited:
            await context["bot"].send_message(
                order["seller_telegram_id"],
                MESSAGES["order_unit_wallet_charged_notify"].format(
                    amount=_format_money(commission),
                    balance=_format_money(wallet["balance"]),
                ),
            )

        # مرحله‌ی ۳: پیام کارشناس را به وضعیت نهایی تغییر می‌دهیم و دکمه‌ها را
        # حذف می‌کنیم تا امکان تأیید دوباره‌ی همان سریال از طریق UI هم گرفته شود
        # (علاوه بر چکِ validation_status بالای همین تابع).
        approved_unit = next(
            (item for item in order.get("units", []) if int(item["index"]) == unit_index),
            unit,
        )
        expert_text = _unit_approved_expert_text(order, approved_unit)
        await context["bot"].send_message(
            callback.from_user.id,
            f"{MESSAGES['order_unit_approved_done']}\n{order['id']} - کالای شماره {unit_index}",
        )
        await _finalize_expert_message(context, callback.message, expert_text, callback.from_user.id)

        if not context["order_service"].has_pending_units(order):
            await context["bot"].send_message(
                order["seller_telegram_id"],
                MESSAGES["order_all_units_done"].format(status=order_status_label(order["status"])),
            )
        return

    # رد
    context["validate_order_id"] = order_id
    context["validate_unit_index"] = unit_index
    context["state"] = ORDER_REJECT_REASON
    # The reject button can belong to a photo message. Bale cannot reliably
    # replace a photo with a text message, so send the next state separately.
    await callback.message.reply(
        MESSAGES["order_select_rejection_reason"],
        components=order_rejection_reasons_keyboard(),
    )


async def choose_order_rejection_reason(callback: CallbackQuery, context: dict):
    reason_key = callback.data.split(":", 1)[1]
    if reason_key == "other":
        context["order_rejection_reason_key"] = reason_key
        await callback.message.edit(MESSAGES["order_custom_rejection_reason"])
        context["state"] = ORDER_CUSTOM_REJECT_REASON
        return
    reason = VALIDATION_REJECTION_REASONS[reason_key]
    order_id = context.pop("validate_order_id")
    unit_index = context.pop("validate_unit_index")
    order = context["order_service"].reject_unit_validation(order_id, unit_index, reason_key, reason)
    await context["bot"].send_message(
        order["seller_telegram_id"],
        MESSAGES["order_unit_rejected_notify"].format(index=unit_index, order_id=order["id"], reason=reason),
    )
    rejected_unit = next((item for item in order.get("units", []) if int(item["index"]) == unit_index), {})
    expert_text = _unit_rejected_expert_text(order, rejected_unit)
    await context["bot"].send_message(
        callback.from_user.id,
        f"{MESSAGES['order_unit_rejected_done']}\n{order['id']} - کالای شماره {unit_index}",
    )
    await _finalize_expert_message(context, callback.message, expert_text, callback.from_user.id)
    if not context["order_service"].has_pending_units(order):
        await context["bot"].send_message(
            order["seller_telegram_id"],
            MESSAGES["order_all_units_done"].format(status=order_status_label(order["status"])),
        )
    context.pop("state", None)


async def receive_custom_rejection_reason(message: Message, context: dict):
    reason_key = context.pop("order_rejection_reason_key")
    order_id = context.pop("validate_order_id")
    unit_index = context.pop("validate_unit_index")
    reason = message.content.strip()
    order = context["order_service"].reject_unit_validation(order_id, unit_index, reason_key, reason)
    await context["bot"].send_message(
        order["seller_telegram_id"],
        MESSAGES["order_unit_rejected_notify"].format(index=unit_index, order_id=order["id"], reason=reason),
    )
    rejected_unit = next((item for item in order.get("units", []) if int(item["index"]) == unit_index), {})
    await message.reply(_unit_rejected_expert_text(order, rejected_unit))
    if not context["order_service"].has_pending_units(order):
        await context["bot"].send_message(
            order["seller_telegram_id"],
            MESSAGES["order_all_units_done"].format(status=order_status_label(order["status"])),
        )
    context.pop("state", None)
