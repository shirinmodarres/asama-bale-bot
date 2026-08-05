import logging

from bot.data.messages import MESSAGES
from bot.data.statuses import status_label
from bot.utils.keyboards import approval_keyboard, request_review_keyboard
from data.static_data import get_sales_experts, get_store

logger = logging.getLogger(__name__)


def format_request(request: dict, title: str) -> str:
    store = get_store(request["store_code"]) or {}
    lines = [
        title,
        f"شماره درخواست: {request['id']}",
        f"فروشگاه: {request['store_code']} - {store.get('name', '')}",
        f"فروشنده: {request['seller_full_name']}",
        f"تلفن: {request['seller_phone']}",
        f"وضعیت: {status_label(request['status'])}",
        "",
        "اقلام:",
    ]
    for index, item in enumerate(request["items"], start=1):
        lines.extend([
            f"{index}) {item['category_name']}",
            f"   مدل: {item['product_model']}",
            f"   تعداد: {item['carton_quantity']} کارتن",
        ])
    return "\n".join(lines)


async def notify_seller_approval(context: dict, expert: dict, seller: dict, store_code: str) -> None:
    store = get_store(store_code) or {"name": ""}
    text = (
        f"{MESSAGES['seller_approval_request']}\n"
        f"فروشگاه: {store_code} - {store['name']}\n"
        f"نام: {seller['full_name']}\n"
        f"تلفن: {seller['phone']}"
    )
    await context["bot"].send_message(
        expert["telegram_id"],
        text,
        components=approval_keyboard("seller", seller["telegram_id"]),
    )


async def notify_expert_request(context: dict, expert: dict, request: dict) -> None:
    await context["bot"].send_message(
        expert["telegram_id"],
        format_request(request, "درخواست کالا برای تأیید کارشناس"),
        components=request_review_keyboard(request["id"], request.get("items", [])),
    )


async def notify_manager_decision(context: dict, request: dict, approved: bool) -> None:
    store = get_store(request["store_code"]) or {}
    expert = get_sales_experts().get(store.get("expert_key"))
    if approved:
        seller_text = MESSAGES["manager_approved_request"]
        expert_text = f"{MESSAGES['manager_approved_for_expert']}\nشماره درخواست: {request['id']}"
    else:
        reason = request.get("manager_reject_reason", "")
        reason_text = f"\nدلیل: {reason}" if reason else ""
        seller_text = f"{MESSAGES['manager_rejected_request']}{reason_text}"
        expert_text = f"{MESSAGES['manager_rejected_for_expert']}\nشماره درخواست: {request['id']}{reason_text}"

    await context["bot"].send_message(request["seller_telegram_id"], seller_text)
    if expert:
        await context["bot"].send_message(expert["telegram_id"], expert_text)
