from bale import Message, CallbackQuery

from bot.data.messages import MESSAGES
from bot.utils.keyboards import (
    admin_management_menu,
    admin_products_menu,
    admin_stores_menu,
    admin_experts_menu,
    admin_bot_menu,
    stores_keyboard,
    experts_keyboard,
    product_status_keyboard,
    product_action_keyboard,
    store_action_keyboard,
    expert_action_keyboard,
    admin_action_requests_keyboard,
    admin_action_request_detail_keyboard,
)
from bot.services.admin_service import AdminService
from data.static_data import get_role, SALES_MANAGER, STORES, SALES_EXPERTS

(
    ADMIN_MANAGE_PRODUCTS,
    ADMIN_MANAGE_STORES,
    ADMIN_MANAGE_EXPERTS,
    ADMIN_MANAGE_BOT,
    ADMIN_PRODUCT_LIST,
    ADMIN_PRODUCT_TOGGLE,
    ADMIN_STORE_LIST,
    ADMIN_STORE_TOGGLE,
    ADMIN_EXPERT_LIST,
    ADMIN_EXPERT_TOGGLE,
    ADMIN_BOT_TOGGLE,
    ADMIN_ACTION_REQUESTS,
    ADMIN_ACTION_REQUEST_APPROVE,
    ADMIN_ACTION_REQUEST_REJECT,
    ADMIN_REJECT_REASON,
) = range(40, 55)


def _get_admin_action_description(request: dict, admin_service: AdminService) -> str:
    """توضیح جزئیات درخواست عملیات مدیریتی برای مدیر"""
    action_type = request.get("action_type")
    payload = request.get("payload", {})
    
    if action_type == "product_toggle":
        category_key = payload.get("category_key", "")
        product_key = payload.get("product_key", "")
        active_flag = payload.get("active", True)
        product = admin_service.get_product(category_key, product_key) or {}
        action_text = "فعال کردن" if active_flag else "غیرفعال کردن"
        return f"{action_text} کالا: {product.get('name', product_key)} ({product.get('category_name', category_key)})"
    
    elif action_type == "store_toggle":
        store_code = payload.get("store_code", "")
        active_flag = payload.get("active", True)
        store = STORES.get(store_code, {})
        action_text = "فعال کردن" if active_flag else "غیرفعال کردن"
        return f"{action_text} فروشگاه: {store_code} - {store.get('name', '')}"
    
    elif action_type == "expert_toggle":
        expert_key = payload.get("expert_key", "")
        active_flag = payload.get("active", True)
        expert = SALES_EXPERTS.get(expert_key, {})
        action_text = "فعال کردن" if active_flag else "غیرفعال کردن"
        return f"{action_text} کارشناس: {expert.get('full_name', expert_key)}"
    
    elif action_type == "bot_toggle":
        active_flag = payload.get("active", True)
        action_text = "فعال کردن" if active_flag else "غیرفعال کردن"
        return f"{action_text} ربات سیستم"
    
    return ""


async def admin_panel(message: Message, context: dict):
    role = get_role(message.author.id)
    if role not in {"admin", "sales_manager"}:
        await message.reply(MESSAGES["not_allowed"])
        return
    await message.reply(MESSAGES["admin_start"], components=admin_management_menu())
    context.pop("state", None)


async def admin_menu_callback(callback: CallbackQuery, context: dict):
    role = get_role(callback.from_user.id)
    if role not in {"admin", "sales_manager"}:
        await callback.message.edit(MESSAGES["not_allowed"])
        return

    admin_service = context["admin_service"]
    data = callback.data

    if data == "admin:main":
        await callback.message.edit(MESSAGES["admin_start"], components=admin_management_menu())
        return
    if data == "admin:products":
        await callback.message.edit(MESSAGES["admin_products_list"], components=admin_products_menu())
        return
    if data == "admin:stores":
        await callback.message.edit(MESSAGES["admin_stores_list"], components=admin_stores_menu())
        return
    if data == "admin:experts":
        await callback.message.edit(MESSAGES["admin_experts_list"], components=admin_experts_menu())
        return
    if data.startswith("admin:product_select:"):
        _, _, category_key, product_key = data.split(":")
        product = admin_service.get_product(category_key, product_key)
        if not product:
            await callback.message.edit(MESSAGES["request_not_found"])
            return
        await callback.message.edit(
            MESSAGES["admin_product_action_prompt"].format(
                title=product["name"],
                category=product["category_name"],
                model=product["model"],
                price=f"{product.get('price', 0):,}",
                status=MESSAGES["active_status"] if product["active"] else MESSAGES["inactive_status"],
            ),
            components=product_action_keyboard(category_key, product_key, product["active"], back_callback="admin:products"),
        )
        return
    if data.startswith("admin:store_select:"):
        _, _, store_code = data.split(":")
        store = admin_service.get_store(store_code)
        if not store:
            await callback.message.edit(MESSAGES["request_not_found"])
            return
        await callback.message.edit(
            MESSAGES["admin_store_action_prompt"].format(
                code=store["code"],
                name=store["name"],
                status=MESSAGES["active_status"] if store["active"] else MESSAGES["inactive_status"],
            ),
            components=store_action_keyboard(store_code, store["active"], back_callback="admin:stores"),
        )
        return
    if data.startswith("admin:expert_select:"):
        _, _, expert_key = data.split(":")
        expert = admin_service.get_expert(expert_key)
        if not expert:
            await callback.message.edit(MESSAGES["request_not_found"])
            return
        await callback.message.edit(
            MESSAGES["admin_expert_action_prompt"].format(
                key=expert["expert_key"],
                name=expert["full_name"],
                status=MESSAGES["active_status"] if expert["active"] else MESSAGES["inactive_status"],
            ),
            components=expert_action_keyboard(expert_key, expert["active"], back_callback="admin:experts"),
        )
        return
    if data == "admin:bot":
        await callback.message.edit(MESSAGES["admin_bot_status"].format(active=MESSAGES["bot_status_on"] if admin_service.bot_active() else MESSAGES["bot_status_off"]), components=admin_bot_menu(admin_service.bot_active()))
        return
    if data == "admin:requests":
        await callback.message.edit(MESSAGES["admin_action_requests"], components=admin_action_requests_keyboard(admin_service.list_admin_action_requests()))
        return

    if data.startswith("admin:product_toggle:"):
        _, _, category_key, product_key, active = data.split(":")
        active_flag = active == "1"
        if role == "admin":
            request = admin_service.create_admin_action_request(
                title=MESSAGES["admin_request_title_product"].format(product_key=product_key),
                action_type="product_toggle",
                payload={"category_key": category_key, "product_key": product_key, "active": active_flag},
                initiated_by=callback.from_user.id,
            )
            await callback.message.edit(MESSAGES["admin_request_created"].format(title=request["title"], request_id=request["id"]))
            try:
                description = _get_admin_action_description(request, admin_service)
                await context["bot"].send_message(
                    SALES_MANAGER["telegram_id"],
                    MESSAGES["admin_action_request_detail_with_desc"].format(
                        title=request["title"],
                        description=description,
                        status=request["status"],
                        created_at=request["created_at"],
                    ),
                    components=admin_action_request_detail_keyboard(request),
                )
            except Exception:
                pass
            return
        admin_service.set_product_active(category_key, product_key, active_flag)
        await callback.message.edit(MESSAGES["product_status_updated"])
        return

    if data.startswith("admin:store_toggle:"):
        _, _, store_code, active = data.split(":")
        active_flag = active == "1"
        if role == "admin":
            request = admin_service.create_admin_action_request(
                title=MESSAGES["admin_request_title_store"].format(store_code=store_code),
                action_type="store_toggle",
                payload={"store_code": store_code, "active": active_flag},
                initiated_by=callback.from_user.id,
            )
            await callback.message.edit(MESSAGES["admin_request_created"].format(title=request["title"], request_id=request["id"]))
            try:
                description = _get_admin_action_description(request, admin_service)
                await context["bot"].send_message(
                    SALES_MANAGER["telegram_id"],
                    MESSAGES["admin_action_request_detail_with_desc"].format(
                        title=request["title"],
                        description=description,
                        status=request["status"],
                        created_at=request["created_at"],
                    ),
                    components=admin_action_request_detail_keyboard(request),
                )
            except Exception:
                pass
            return
        admin_service.set_store_active(store_code, active_flag)
        await callback.message.edit(MESSAGES["store_status_updated"])

    if data.startswith("admin:expert_toggle:"):
        _, _, expert_key, active = data.split(":")
        active_flag = active == "1"
        if role == "admin":
            request = admin_service.create_admin_action_request(
                title=MESSAGES["admin_request_title_expert"].format(expert_key=expert_key),
                action_type="expert_toggle",
                payload={"expert_key": expert_key, "active": active_flag},
                initiated_by=callback.from_user.id,
            )
            await callback.message.edit(MESSAGES["admin_request_created"].format(title=request["title"], request_id=request["id"]))
            try:
                description = _get_admin_action_description(request, admin_service)
                await context["bot"].send_message(
                    SALES_MANAGER["telegram_id"],
                    MESSAGES["admin_action_request_detail_with_desc"].format(
                        title=request["title"],
                        description=description,
                        status=request["status"],
                        created_at=request["created_at"],
                    ),
                    components=admin_action_request_detail_keyboard(request),
                )
            except Exception:
                pass
            return
        admin_service.set_expert_active(expert_key, active_flag)
        await callback.message.edit(MESSAGES["expert_status_updated"])

    if data.startswith("admin:bot_toggle:"):
        _, _, active = data.split(":")
        active_flag = active == "1"
        if role == "admin":
            request = admin_service.create_admin_action_request(
                title=MESSAGES["admin_request_title_bot"],
                action_type="bot_toggle",
                payload={"active": active_flag},
                initiated_by=callback.from_user.id,
            )
            await callback.message.edit(MESSAGES["admin_request_created"].format(title=request["title"], request_id=request["id"]))
            try:
                description = _get_admin_action_description(request, admin_service)
                await context["bot"].send_message(
                    SALES_MANAGER["telegram_id"],
                    MESSAGES["admin_action_request_detail_with_desc"].format(
                        title=request["title"],
                        description=description,
                        status=request["status"],
                        created_at=request["created_at"],
                    ),
                    components=admin_action_request_detail_keyboard(request),
                )
            except Exception:
                pass
            return
        admin_service.set_bot_active(active_flag)
        await callback.message.edit(MESSAGES["bot_status_updated"])  # should not happen for sales manager

    if data.startswith("admin:request:"):
        request_id = int(data.split(":", 2)[2])
        request = admin_service.get_admin_action_request(request_id)
        if not request:
            await callback.message.edit(MESSAGES["request_not_found"])
            return
        components = admin_action_request_detail_keyboard(request)
        await callback.message.edit(
            MESSAGES["admin_action_request_detail"].format(
                title=request["title"],
                status=request["status"],
                created_at=request["created_at"],
            ),
            components=components,
        )
        return

    if data.startswith("admin:approve:") or data.startswith("admin:reject:"):
        _, action, request_id_text = data.split(":")
        request_id = int(request_id_text)
        if role != "sales_manager":
            await callback.message.edit(MESSAGES["not_allowed"])
            return
        if action == "approve":
            request = admin_service.approve_admin_action_request(request_id, callback.from_user.id)
            if not request:
                await callback.message.edit(MESSAGES["request_not_found"])
                return
            await callback.message.edit(MESSAGES["admin_request_approved"].format(request_id=request_id))
            # notify initiating admin
            try:
                await context["bot"].send_message(
                    request.get("initiated_by"),
                    MESSAGES.get("manager_approved_request", "درخواست شما توسط مدیر فروش تأیید شد."),
                )
            except Exception:
                pass
            return
        context["admin_reject_request_id"] = request_id
        await callback.message.edit(MESSAGES["ask_reject_reason"])
        context["state"] = ADMIN_REJECT_REASON
        return


async def receive_admin_reject_reason(message: Message, context: dict):
    if context.get("state") != ADMIN_REJECT_REASON:
        await message.reply(MESSAGES["not_allowed"])
        return
    request_id = context.pop("admin_reject_request_id", None)
    if not request_id:
        await message.reply(MESSAGES["request_not_found"])
        context.pop("state", None)
        return
    request = context["admin_service"].reject_admin_action_request(request_id, message.author.id, message.content.strip())
    if not request:
        await message.reply(MESSAGES["request_not_found"])
        context.pop("state", None)
        return
    await message.reply(MESSAGES["admin_request_rejected"].format(request_id=request_id))
    try:
        await context["bot"].send_message(
            request.get("initiated_by"),
            MESSAGES["manager_rejected_request_with_reason"].format(
                reason=request.get("reject_reason", "")
            ),
        )
    except Exception:
        pass
    context.pop("state", None)
