from datetime import datetime, timezone
from math import ceil

from pymongo import ASCENDING, ReturnDocument

from bot.data.messages import MESSAGES
from bot.utils.datetime_format import jalali_datetime_parts


DEFAULT_COMMISSION_RATE = 4
CALCULATION_THRESHOLD_FULL_AMOUNT = "threshold_full_amount"
BASIS_SALES_AMOUNT = "sales_amount"
BASIS_SALES_QUANTITY = "sales_quantity"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def month_from_datetime(value: str) -> str:
    _jalali_date, jalali_month, _tehran_time = jalali_datetime_parts(value or utc_now())
    return jalali_month


def _persian_digits(value) -> str:
    english = "0123456789"
    persian = "۰۱۲۳۴۵۶۷۸۹"
    result = str(value)
    for e, p in zip(english, persian):
        result = result.replace(e, p)
    return result


def _format_rial(rial_amount: int) -> str:
    return _persian_digits(f"{int(rial_amount):,}")


def _format_rate(value) -> str:
    number = float(value or 0)
    if number.is_integer():
        text = str(int(number))
    else:
        text = f"{number:.2f}".rstrip("0").rstrip(".")
    return _persian_digits(text)


def _jalali_days_remaining() -> int:
    jalali_date, _jalali_month, _tehran_time = jalali_datetime_parts(utc_now())
    year_text, month_text, day_text = jalali_date.split("/")
    month = int(month_text)
    day = int(day_text)
    if month <= 6:
        month_length = 31
    elif month <= 11:
        month_length = 30
    else:
        year = int(year_text)
        month_length = 30 if ((year - 474) % 2820 + 474 + 38) * 682 % 2816 < 682 else 29
    return max(month_length - day, 0)


class CommissionService:
    def __init__(self, db, wallet_service, user_service):
        self.db = db
        self.orders = db["orders"]
        self.returns = db["product_returns"]
        self.rules = db["commission_rules"]
        self.performance = db["store_monthly_performance"]
        self.wallet_service = wallet_service
        self.user_service = user_service
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.rules.create_index([("month", ASCENDING), ("active", ASCENDING), ("version", ASCENDING)])
        self.performance.create_index([("store_code", ASCENDING), ("month", ASCENDING)], unique=True)
        self.performance.create_index([("month", ASCENDING), ("updated_at", ASCENDING)])

    def recalculate_for_sale(self, order: dict, unit: dict) -> dict | None:
        decision_at = unit.get("validation_decision_at") or order.get("updated_at") or order.get("created_at") or utc_now()
        event_id = f"sale:{order['id']}:{unit['index']}"
        return self.recalculate_store_month(order["store_code"], month_from_datetime(decision_at), event_id=event_id)

    def recalculate_for_return(self, product_return: dict) -> dict | None:
        month = product_return.get("sale_month") or month_from_datetime(product_return.get("sold_at") or product_return.get("created_at"))
        event_id = f"return:{product_return['return_id']}"
        return self.recalculate_store_month(product_return["store_code"], month, event_id=event_id)

    def recalculate_store_month(
        self,
        store_code: str,
        month: str,
        post_delta: bool = True,
        mark_posted_to_entitlement: bool = False,
        event_id: str | None = None,
    ) -> dict | None:
        seller = self.user_service.get_approved_seller_by_store(store_code)
        if not seller:
            return None

        gross_amount, gross_qty = self._approved_sales_totals(store_code, month)
        return_amount, return_qty = self._approved_return_totals(store_code, month)
        net_amount = max(gross_amount - return_amount, 0)
        net_qty = max(gross_qty - return_qty, 0)

        rule = self.active_rule_for_month(month)
        basis = rule.get("basis", BASIS_SALES_AMOUNT)
        metric = net_qty if basis == BASIS_SALES_QUANTITY else net_amount
        rate = self._rate_for_metric(rule, metric)
        entitlement = ceil(net_amount * rate / 100)

        existing = self.performance.find_one({"store_code": str(store_code), "month": month}) or {}
        previous_amount = int(existing.get("net_sales_amount", 0) or 0)
        previous_qty = int(existing.get("net_sales_quantity", existing.get("net_sales_qty", 0)) or 0)
        posted = int(existing.get("wallet_commission_posted", 0) or 0)
        if mark_posted_to_entitlement and not existing:
            posted = entitlement
        delta = entitlement - posted
        previous_metric = previous_qty if basis == BASIS_SALES_QUANTITY else previous_amount
        previous_rate = self._rate_for_metric(rule, previous_metric)
        threshold = self._current_threshold(rule, metric)
        next_tier = self._next_tier(rule, metric)
        threshold_crossed = bool(existing and float(rate) > float(previous_rate))

        now = utc_now()
        document = {
            "store_code": str(store_code),
            "seller_telegram_id": int(seller["telegram_id"]),
            "month": month,
            "gross_sales_amount": gross_amount,
            "gross_sales_quantity": gross_qty,
            "gross_sales_qty": gross_qty,
            "approved_return_amount": return_amount,
            "approved_return_quantity": return_qty,
            "approved_return_qty": return_qty,
            "net_sales_amount": net_amount,
            "net_sales_quantity": net_qty,
            "net_sales_qty": net_qty,
            "applied_rule": {
                "commission_rule_id": str(rule.get("_id", "")) if rule.get("_id") else None,
                "month": rule.get("month"),
                "version": rule.get("version"),
                "basis": basis,
                "calculation_type": rule.get("calculation_type", CALCULATION_THRESHOLD_FULL_AMOUNT),
                "tiers": rule.get("tiers", []),
            },
            "commission_rule_id": str(rule.get("_id", "")) if rule.get("_id") else None,
            "current_commission_rate": rate,
            "commission_rate": rate,
            "commission_entitlement": entitlement,
            "wallet_commission_posted": posted,
            "next_threshold": next_tier.get("min") if next_tier else None,
            "next_commission_rate": next_tier.get("rate") if next_tier else None,
            "last_delta": delta,
            "threshold_crossed": threshold_crossed,
            "updated_at": now,
        }

        self.performance.update_one(
            {"store_code": str(store_code), "month": month},
            {"$set": document, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

        if post_delta and delta:
            transaction_type = "credit" if delta > 0 else "debit"
            event_part = str(event_id or "manual").replace(":", "-")
            transaction_id = f"wallet:commission_adjustment:{store_code}:{month}:{posted}:{entitlement}:{event_part}"
            transaction, applied = self.wallet_service.apply_transaction(
                telegram_id=seller["telegram_id"],
                store_code=store_code,
                transaction_type=transaction_type,
                source="commission_adjustment",
                amount=abs(delta),
                description=f"به‌روزرسانی پورسانت ماه {month}",
                transaction_id=transaction_id,
                extra_fields={
                    "commission_month": month,
                    "commission_entitlement": entitlement,
                    "previous_wallet_commission_posted": posted,
                },
                allow_negative=True,
            )
            self.performance.find_one_and_update(
                {"store_code": str(store_code), "month": month},
                {
                    "$set": {
                        "wallet_commission_posted": entitlement,
                        "last_wallet_transaction_id": transaction["transaction_id"],
                        "last_wallet_transaction_applied": bool(applied),
                        "last_wallet_delta": delta,
                        "last_wallet_balance": transaction.get("balance_after"),
                        "updated_at": utc_now(),
                    }
                },
                return_document=ReturnDocument.AFTER,
            )

        performance = self.performance.find_one({"store_code": str(store_code), "month": month}, {"_id": 0})
        if performance:
            performance["previous_net_sales_amount"] = previous_amount
            performance["previous_net_sales_quantity"] = previous_qty
            performance["previous_commission_rate"] = previous_rate
            performance["threshold_crossed"] = threshold_crossed
            performance["next_threshold"] = next_tier.get("min") if next_tier else None
            performance["next_commission_rate"] = next_tier.get("rate") if next_tier else None
            performance["current_threshold"] = threshold.get("min") if threshold else None
            performance["last_delta"] = delta
            performance["wallet_balance"] = self.wallet_service.get_balance(seller["telegram_id"])
        return performance

    def active_rule_for_month(self, month: str) -> dict:
        rule = self.rules.find_one(
            {"month": month, "active": True},
            sort=[("version", -1)],
        )
        if rule:
            return rule
        return {
            "month": month,
            "version": 1,
            "basis": BASIS_SALES_AMOUNT,
            "calculation_type": CALCULATION_THRESHOLD_FULL_AMOUNT,
            "tiers": [{"min": 0, "max": None, "rate": DEFAULT_COMMISSION_RATE}],
            "active": True,
            "fallback": True,
        }

    def create_rule(
        self,
        month: str,
        basis: str,
        tiers: list[dict],
        admin_telegram_id: int | None = None,
    ) -> dict:
        if basis not in {BASIS_SALES_AMOUNT, BASIS_SALES_QUANTITY}:
            raise ValueError("invalid basis")
        if not tiers:
            raise ValueError("tiers required")
        normalized_tiers = sorted(
            [
                {
                    "min": int(tier.get("min", 0) or 0),
                    "max": tier.get("max"),
                    "rate": float(tier.get("rate", 0) or 0),
                }
                for tier in tiers
            ],
            key=lambda tier: tier["min"],
        )
        last = self.rules.find_one({"month": month}, sort=[("version", -1)]) or {}
        version = int(last.get("version", 0) or 0) + 1
        now = utc_now()
        self.rules.update_many({"month": month, "active": True}, {"$set": {"active": False, "updated_at": now}})
        document = {
            "month": month,
            "version": version,
            "basis": basis,
            "calculation_type": CALCULATION_THRESHOLD_FULL_AMOUNT,
            "tiers": normalized_tiers,
            "active": True,
            "created_by": admin_telegram_id,
            "created_at": now,
            "updated_at": now,
        }
        self.rules.insert_one(document)
        document["_id"] = str(document["_id"])
        return document

    def build_realtime_message(self, performance: dict | None) -> str:
        if not performance:
            return ""
        rule = performance.get("applied_rule", {})
        basis = rule.get("basis", BASIS_SALES_AMOUNT)
        current_sales = int(performance.get("net_sales_amount", 0) or 0)
        current_metric = int(performance.get("net_sales_quantity" if basis == BASIS_SALES_QUANTITY else "net_sales_amount", 0) or 0)
        current_rate = performance.get("current_commission_rate", performance.get("commission_rate", 0))
        entitlement = int(performance.get("commission_entitlement", 0) or 0)
        wallet_balance = int(performance.get("wallet_balance", 0) or 0)
        delta = int(performance.get("last_delta", 0) or 0)
        next_threshold = performance.get("next_threshold")
        next_rate = performance.get("next_commission_rate")
        previous_sales = int(performance.get("previous_net_sales_amount", 0) or 0)
        threshold_crossed = bool(performance.get("threshold_crossed"))
        current_threshold = performance.get("current_threshold")

        motivational = self._motivational_message(
            current_sales=current_sales,
            previous_sales=previous_sales,
            current_metric=current_metric,
            current_rate=current_rate,
            entitlement=entitlement,
            next_threshold=next_threshold,
            next_rate=next_rate,
            threshold_crossed=threshold_crossed,
            current_threshold=current_threshold,
        )
        wallet_message = ""
        if delta > 0:
            wallet_message = MESSAGES["commission_wallet_increased"].format(
                amount=_format_rial(delta),
                balance=_format_rial(wallet_balance),
            )
        elif delta < 0:
            wallet_message = MESSAGES["commission_wallet_decreased"].format(
                amount=_format_rial(abs(delta)),
                balance=_format_rial(wallet_balance),
            )
        distance = (
            MESSAGES["commission_no_next_rate"]
            if not next_threshold
            else f"{_format_rial(max(int(next_threshold) - current_metric, 0))} ریال"
        )
        summary = MESSAGES["monthly_commission_updated"].format(
            sales=_format_rial(current_sales),
            rate=_format_rate(current_rate),
            entitlement=_format_rial(entitlement),
            balance=_format_rial(wallet_balance),
        )
        summary = f"{summary}\n{MESSAGES['commission_next_distance'].format(distance=distance)}"
        return "\n\n".join(part for part in [motivational, wallet_message, summary] if part)

    def _motivational_message(
        self,
        current_sales: int,
        previous_sales: int,
        current_metric: int,
        current_rate,
        entitlement: int,
        next_threshold,
        next_rate,
        threshold_crossed: bool,
        current_threshold,
    ) -> str:
        if threshold_crossed:
            threshold = int(current_threshold or current_metric)
            return MESSAGES["commission_threshold_crossed_1"].format(
                threshold=_format_rial(threshold),
                current_rate=_format_rate(current_rate),
                commission_entitlement=_format_rial(entitlement),
            )

        if not next_threshold or not next_rate:
            return MESSAGES["commission_threshold_crossed_2"].format(
                current_rate=_format_rate(current_rate),
                current_sales=_format_rial(current_sales),
                commission_entitlement=_format_rial(entitlement),
            )

        remaining = max(int(next_threshold) - current_metric, 0)
        progress = int(min((current_metric / int(next_threshold)) * 100, 100)) if int(next_threshold) else 0
        days_remaining = _jalali_days_remaining()
        if previous_sales == 0:
            return MESSAGES["commission_month_start_1"].format(
                threshold=_format_rial(int(next_threshold)),
                current_rate=_format_rate(current_rate),
                next_rate=_format_rate(next_rate),
            )
        if remaining <= int(next_threshold) * 0.15:
            return MESSAGES["commission_near_threshold_1"].format(
                current_sales=_format_rial(current_sales),
                remaining_amount=_format_rial(remaining),
                threshold=_format_rial(int(next_threshold)),
                current_rate=_format_rate(current_rate),
                next_rate=_format_rate(next_rate),
            )
        if days_remaining <= 5:
            return MESSAGES["commission_end_month"].format(
                days_remaining=_persian_digits(days_remaining),
                remaining_amount=_format_rial(remaining),
                threshold=_format_rial(int(next_threshold)),
                next_rate=_format_rate(next_rate),
            )
        return MESSAGES["commission_progress_2"].format(
            progress_percent=_persian_digits(progress),
            threshold=_format_rial(int(next_threshold)),
            current_sales=_format_rial(current_sales),
            commission_entitlement=_format_rial(entitlement),
            current_rate=_format_rate(current_rate),
        )

    def _approved_sales_totals(self, store_code: str, month: str) -> tuple[int, int]:
        total_amount = 0
        total_qty = 0
        orders = self.orders.find(
            {"store_code": str(store_code), "units.validation_status": "approved"},
            {"_id": 0},
        )
        for order in orders:
            for unit in order.get("units", []):
                if unit.get("validation_status") != "approved":
                    continue
                decision_at = unit.get("validation_decision_at") or order.get("updated_at") or order.get("created_at")
                if month_from_datetime(decision_at) != month:
                    continue
                total_qty += 1
                total_amount += int(unit.get("product_price") or order.get("product_price") or 0)
        return total_amount, total_qty

    def _approved_return_totals(self, store_code: str, month: str) -> tuple[int, int]:
        total_amount = 0
        total_qty = 0
        returns = self.returns.find(
            {"store_code": str(store_code), "status": "approved"},
            {"_id": 0},
        )
        for product_return in returns:
            sale_month = product_return.get("sale_month") or month_from_datetime(
                product_return.get("sold_at") or product_return.get("created_at")
            )
            if sale_month != month:
                continue
            total_qty += int(product_return.get("quantity", 1) or 1)
            total_amount += int(product_return.get("product_price") or 0)
        return total_amount, total_qty

    @staticmethod
    def _rate_for_metric(rule: dict, metric: int) -> float:
        selected_rate = 0
        for tier in rule.get("tiers", []):
            minimum = int(tier.get("min", 0) or 0)
            maximum = tier.get("max")
            if metric < minimum:
                continue
            if maximum not in (None, "") and metric > int(maximum):
                continue
            selected_rate = float(tier.get("rate", 0) or 0)
        return selected_rate

    @staticmethod
    def _current_threshold(rule: dict, metric: int) -> dict | None:
        selected = None
        for tier in rule.get("tiers", []):
            minimum = int(tier.get("min", 0) or 0)
            maximum = tier.get("max")
            if metric < minimum:
                continue
            if maximum not in (None, "") and metric > int(maximum):
                continue
            selected = tier
        return selected

    @staticmethod
    def _next_tier(rule: dict, metric: int) -> dict | None:
        candidates = [
            tier
            for tier in rule.get("tiers", [])
            if int(tier.get("min", 0) or 0) > metric
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda tier: int(tier.get("min", 0) or 0))[0]
