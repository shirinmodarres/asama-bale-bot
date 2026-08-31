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
    wallet_admin_actions_keyboard,
    wallet_admin_confirm_keyboard,
)
from bot.services.admin_service import AdminService
from bot.services.wallet_service import SOURCE_LABELS_FA, TYPE_LABELS_FA, manual_transaction_id
from bot.utils.normalize import normalize_digits
from data.static_data import get_role, get_sales_manager

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
    ADMIN_WALLET_AMOUNT,
    ADMIN_WALLET_DESCRIPTION,
) = range(40, 57)


def _format_money(amount: int) -> str:
    if amount in (None, ""):
        return "-"
    return f"{int(amount):,}"


def _wallet_operation_label(operation: str) -> str:
    return {
        "credit": "افزایش موجودی",
        "debit": "کاهش موجودی",
        "settlement": "تسویه / ارسال به مالی",
    }.get(operation, operation)


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
        store = admin_service.get_store(store_code) or {}
        action_text = "فعال کردن" if active_flag else "غیرفعال کردن"
        return f"{action_text} فروشگاه: {store_code} - {store.get('name', '')}"
    
    elif action_type == "expert_toggle":
        expert_key = payload.get("expert_key", "")
        active_flag = payload.get("active", True)
        expert = admin_service.get_expert(expert_key) or {}
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
    if data == "admin:wallet":
        if role != "admin":
            await callback.message.edit(MESSAGES["not_allowed"])
            return
        stores = [store for store in admin_service.list_stores() if store.get("active", True)]
        await callback.message.edit(
            MESSAGES["admin_wallet_store_list"],
            components=stores_keyboard(stores, "admin:wallet_store", back_callback="admin:main"),
        )
        return
    if data.startswith("admin:wallet_store:"):
        if role != "admin":
            await callback.message.edit(MESSAGES["not_allowed"])
            return
        store_code = data.rsplit(":", 1)[1]
        await _show_wallet_detail(callback.message, context, store_code)
        return
    if data.startswith("admin:wallet_history:"):
        if role != "admin":
            await callback.message.edit(MESSAGES["not_allowed"])
            return
        store_code = data.rsplit(":", 1)[1]
        await _show_wallet_history(callback.message, context, store_code)
        return
    if data.startswith("admin:wallet_action:"):
        if role != "admin":
            await callback.message.edit(MESSAGES["not_allowed"])
            return
        _, _, store_code, operation = data.split(":")
        seller = context["user_service"].get_approved_seller_by_store(store_code)
        if not seller:
            await callback.message.edit(MESSAGES["admin_wallet_no_seller"])
            return
        context["admin_wallet_draft"] = {
            "store_code": store_code,
            "operation": operation,
            "seller_telegram_id": seller["telegram_id"],
            "seller_name": seller.get("full_name", ""),
        }
        await callback.message.edit(MESSAGES["admin_wallet_ask_amount"])
        context["state"] = ADMIN_WALLET_AMOUNT
        return
    if data == "admin:wallet_cancel":
        context.pop("admin_wallet_draft", None)
        context.pop("state", None)
        await callback.message.edit(MESSAGES["admin_wallet_cancelled"])
        return
    if data == "admin:wallet_confirm":
        if role != "admin":
            await callback.message.edit(MESSAGES["not_allowed"])
            return
        await _confirm_wallet_operation(callback, context)
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
                    get_sales_manager()["telegram_id"],
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
                    get_sales_manager()["telegram_id"],
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
                    get_sales_manager()["telegram_id"],
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
                    get_sales_manager()["telegram_id"],
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


async def _show_wallet_detail(message, context: dict, store_code: str):
    store = context["admin_service"].get_store(store_code)
    seller = context["user_service"].get_approved_seller_by_store(store_code)
    if not seller:
        await message.edit(MESSAGES["admin_wallet_no_seller"])
        return
    balance = context["wallet_service"].get_balance(seller["telegram_id"])
    await message.edit(
        MESSAGES["admin_wallet_detail"].format(
            store_code=store_code,
            store_name=(store or {}).get("name", ""),
            seller_name=seller.get("full_name", ""),
            balance=_format_money(balance),
        ),
        components=wallet_admin_actions_keyboard(store_code),
    )


async def _show_wallet_history(message, context: dict, store_code: str):
    seller = context["user_service"].get_approved_seller_by_store(store_code)
    if not seller:
        await message.edit(MESSAGES["admin_wallet_no_seller"])
        return
    transactions = context["wallet_service"].list_transactions(seller["telegram_id"], limit=10)
    if not transactions:
        await message.edit(MESSAGES["admin_wallet_history_empty"], components=wallet_admin_actions_keyboard(store_code))
        return
    lines = [MESSAGES["admin_wallet_history_title"]]
    for transaction in transactions:
        sign = "+" if transaction.get("type") == "credit" else "-"
        date_text = transaction.get("jalali_date", "")
        if transaction.get("tehran_time"):
            date_text = f"{date_text} {transaction['tehran_time']}".strip()
        lines.append(
            MESSAGES["admin_wallet_history_line"].format(
                date=date_text,
                type=TYPE_LABELS_FA.get(transaction.get("type"), transaction.get("type", "")),
                source=SOURCE_LABELS_FA.get(transaction.get("source"), transaction.get("source", "")),
                amount=f"{sign}{_format_money(transaction.get('amount', 0))}",
                description=transaction.get("description", ""),
                balance_before=_format_money(transaction.get("balance_before", 0)),
                balance_after=_format_money(transaction.get("balance_after", 0)),
            )
        )
    await message.edit("\n\n".join(lines), components=wallet_admin_actions_keyboard(store_code))


async def receive_wallet_amount(message: Message, context: dict):
    draft = context.get("admin_wallet_draft")
    if not draft:
        await message.reply(MESSAGES["request_not_found"])
        context.pop("state", None)
        return
    text = normalize_digits(message.content or "").replace(",", "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.reply(MESSAGES["admin_wallet_invalid_amount"])
        return

    amount = int(text)
    balance = context["wallet_service"].get_balance(draft["seller_telegram_id"])
    operation = draft["operation"]
    if operation in {"debit", "settlement"} and amount > balance:
        await message.reply(MESSAGES["admin_wallet_insufficient"])
        return

    draft["amount"] = amount
    draft["balance_before"] = balance
    draft["balance_after"] = balance + amount if operation == "credit" else balance - amount

    if operation == "settlement":
        draft["description"] = "تسویه و ارسال به مالی"
        await _send_wallet_confirmation(message, context)
        return

    await message.reply(MESSAGES["admin_wallet_ask_description"])
    context["state"] = ADMIN_WALLET_DESCRIPTION


async def receive_wallet_description(message: Message, context: dict):
    draft = context.get("admin_wallet_draft")
    if not draft:
        await message.reply(MESSAGES["request_not_found"])
        context.pop("state", None)
        return
    draft["description"] = (message.content or "").strip()
    await _send_wallet_confirmation(message, context)


async def _send_wallet_confirmation(message: Message, context: dict):
    draft = context["admin_wallet_draft"]
    store = context["admin_service"].get_store(draft["store_code"]) or {}
    await message.reply(
        MESSAGES["admin_wallet_confirm"].format(
            store_name=store.get("name", draft["store_code"]),
            operation=_wallet_operation_label(draft["operation"]),
            amount=_format_money(draft["amount"]),
            balance_before=_format_money(draft["balance_before"]),
            balance_after=_format_money(draft["balance_after"]),
            description=draft["description"],
        ),
        components=wallet_admin_confirm_keyboard(),
    )
    context.pop("state", None)


async def _confirm_wallet_operation(callback: CallbackQuery, context: dict):
    draft = context.get("admin_wallet_draft")
    if not draft:
        await callback.message.edit(MESSAGES["request_not_found"])
        return

    operation = draft["operation"]
    transaction_type = "credit" if operation == "credit" else "debit"
    source = "settlement" if operation == "settlement" else "manual_admin"
    try:
        transaction, _applied = context["wallet_service"].apply_transaction(
            telegram_id=draft["seller_telegram_id"],
            store_code=draft["store_code"],
            transaction_type=transaction_type,
            source=source,
            amount=draft["amount"],
            description=draft["description"],
            transaction_id=manual_transaction_id(source, draft["seller_telegram_id"]),
            admin_telegram_id=callback.from_user.id,
        )
    except ValueError:
        await callback.message.edit(MESSAGES["admin_wallet_insufficient"])
        return

    await _notify_seller_wallet_changed(callback, context, draft, transaction)
    context.pop("admin_wallet_draft", None)
    context.pop("state", None)
    await callback.message.edit(MESSAGES["admin_wallet_done"])


async def _notify_seller_wallet_changed(
    callback: CallbackQuery,
    context: dict,
    draft: dict,
    transaction: dict,
) -> None:
    try:
        await context["bot"].send_message(
            draft["seller_telegram_id"],
            MESSAGES["seller_wallet_admin_changed"].format(
                operation=_wallet_operation_label(draft["operation"]),
                amount=_format_money(transaction.get("amount", draft["amount"])),
                balance_before=_format_money(transaction.get("balance_before", draft.get("balance_before", 0))),
                balance_after=_format_money(transaction.get("balance_after", draft.get("balance_after", 0))),
                description=transaction.get("description", draft.get("description", "")),
            ),
        )
    except Exception:
        pass
