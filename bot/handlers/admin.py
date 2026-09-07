from bale import Message, InputFile

from bot.data.messages import MESSAGES
from bot.services.commission_service import BASIS_SALES_AMOUNT, BASIS_SALES_QUANTITY
from bot.services.excel_service import ExcelService
from bot.utils.normalize import normalize_digits
from data.static_data import expert_store_codes, get_role


async def bot_info(message: Message, context: dict):
    role = get_role(message.author.id)
    if role != "admin":
        await message.reply(MESSAGES["bot_info_not_allowed"])
        return
    request_service = context["request_service"]
    requests = request_service.list_requests()
    await message.reply(f"تعداد درخواست‌ها: {len(requests)}")


async def export_requests(message: Message, context: dict):
    role = get_role(message.author.id)
    if role not in {"expert", "sales_manager", "admin"}:
        await message.reply(MESSAGES["export_not_allowed"])
        return

    request_service = context["request_service"]
    if role == "expert":
        requests = request_service.list_requests_for_stores(expert_store_codes(message.author.id))
    else:
        requests = request_service.list_requests()

    path = ExcelService().export_requests(requests)
    with path.open("rb") as file:
        await message.reply_document(InputFile(file.read(), file_name="goods_requests.xlsx"))
    path.unlink(missing_ok=True)


async def export_orders(message: Message, context: dict):
    role = get_role(message.author.id)
    if role not in {"sales_manager", "admin"}:
        await message.reply(MESSAGES["export_not_allowed"])
        return

    orders = context["order_service"].list_orders()
    path = ExcelService().export_orders(orders)
    with path.open("rb") as file:
        await message.reply_document(InputFile(file.read(), file_name="product_orders.xlsx"))
    path.unlink(missing_ok=True)


async def create_commission_rule(message: Message, context: dict):
    if get_role(message.author.id) != "admin":
        await message.reply(MESSAGES["export_not_allowed"])
        return
    parts = (message.content or "").strip().split(maxsplit=3)
    if len(parts) != 4:
        await message.reply(MESSAGES["commission_rule_usage"])
        return
    _command, month, basis, tiers_text = parts
    if basis not in {BASIS_SALES_AMOUNT, BASIS_SALES_QUANTITY}:
        await message.reply(MESSAGES["commission_rule_usage"])
        return
    tiers = []
    try:
        for item in tiers_text.split(","):
            threshold, rate = item.split(":", 1)
            tiers.append({"min": int(normalize_digits(threshold)), "max": None, "rate": float(normalize_digits(rate))})
        tiers = sorted(tiers, key=lambda tier: tier["min"])
        for index, tier in enumerate(tiers[:-1]):
            tier["max"] = tiers[index + 1]["min"] - 1
    except Exception:
        await message.reply(MESSAGES["commission_rule_usage"])
        return
    rule = context["commission_service"].create_rule(month, basis, tiers, admin_telegram_id=message.author.id)
    await message.reply(MESSAGES["commission_rule_saved"].format(month=rule["month"], version=rule["version"]))
