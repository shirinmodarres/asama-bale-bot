from bale import Message, CallbackQuery

from bot.data.messages import MESSAGES
from bot.services.notification_service import notify_manager_decision
from bot.utils.normalize import normalize_digits
from data.static_data import get_role

MANAGER_REJECT_REASON = 30


async def manager_request_callback(callback: CallbackQuery, context: dict):
    if get_role(callback.from_user.id) not in {"sales_manager", "admin"}:
        await callback.message.edit(MESSAGES["not_allowed"])
        return

    _prefix, action, request_id_text = callback.data.split(":")
    request_id = int(normalize_digits(request_id_text))
    request_service = context["request_service"]
    request = request_service.get_request(request_id)
    if not request:
        await callback.message.edit(MESSAGES["request_not_found"])
        return

    if action == "approve":
        request = request_service.approve_by_manager(request_id)
        await notify_manager_decision(context, request, approved=True)
        await callback.message.edit(MESSAGES["manager_approved_done"])
        return

    context["manager_reject_request_id"] = request_id
    await callback.message.edit(MESSAGES["ask_reject_reason"])
    context["state"] = MANAGER_REJECT_REASON


async def receive_manager_reject_reason(message: Message, context: dict):
    if context.get("state") != MANAGER_REJECT_REASON:
        await message.reply(MESSAGES["not_allowed"])
        return
    request_id = context.pop("manager_reject_request_id", None)
    if not request_id:
        await message.reply(MESSAGES["request_not_found"])
        context.pop("state", None)
        return
    reason = message.content.strip()
    request = context["request_service"].reject_by_manager(request_id, reason)
    await notify_manager_decision(context, request, approved=False)
    await message.reply(MESSAGES["request_rejected"])
    context.pop("state", None)