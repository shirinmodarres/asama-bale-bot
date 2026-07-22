PENDING_SELLER_APPROVAL = "pending_seller_approval"
SELLER_REJECTED = "seller_rejected"
ACTIVE = "active"
PENDING_EXPERT = "pending_expert"
PENDING_SELLER_CONFIRMATION = "pending_seller_confirmation"
REJECTED_BY_EXPERT = "rejected_by_expert"
APPROVED_BY_EXPERT = "approved_by_expert"
PENDING_MANAGER = "pending_manager"
REJECTED_BY_MANAGER = "rejected_by_manager"
APPROVED_BY_MANAGER = "approved_by_manager"
CANCELLED = "cancelled"

ORDER_PENDING_EXPERT_VALIDATION = "pending_expert_validation"
ORDER_APPROVED_BY_EXPERT = "approved_by_expert"
ORDER_REJECTED_BY_EXPERT = "rejected_by_expert"
ORDER_PARTIALLY_APPROVED_BY_EXPERT = "partially_approved_by_expert"
ORDER_CANCELLED = "cancelled"

STATUS_LABELS_FA = {
    PENDING_SELLER_APPROVAL: "در انتظار تأیید فروشنده",
    SELLER_REJECTED: "فروشنده رد شده",
    ACTIVE: "فعال",
    PENDING_EXPERT: "در انتظار بررسی کارشناس",
    PENDING_SELLER_CONFIRMATION: "در انتظار تأیید فروشنده",
    REJECTED_BY_EXPERT: "رد شده توسط کارشناس",
    APPROVED_BY_EXPERT: "نهایی شده توسط کارشناس",
    PENDING_MANAGER: "در انتظار بررسی مدیر فروش",
    REJECTED_BY_MANAGER: "رد شده توسط مدیر فروش",
    APPROVED_BY_MANAGER: "تایید نهایی شده",
    CANCELLED: "لغو شده",
}


def status_label(status: str) -> str:
    return STATUS_LABELS_FA.get(status, status)


ORDER_STATUS_LABELS_FA = {
    ORDER_PENDING_EXPERT_VALIDATION: "در انتظار اعتبارسنجی کارشناس",
    ORDER_APPROVED_BY_EXPERT: "تایید شده توسط کارشناس",
    ORDER_REJECTED_BY_EXPERT: "رد شده توسط کارشناس",
    ORDER_PARTIALLY_APPROVED_BY_EXPERT: "تایید/رد بخشی توسط کارشناس",
    ORDER_CANCELLED: "لغو شده",
}


def order_status_label(status: str) -> str:
    return ORDER_STATUS_LABELS_FA.get(status, status)
