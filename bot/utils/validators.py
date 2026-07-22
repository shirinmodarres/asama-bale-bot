from bot.utils.normalize import normalize_digits


def normalize_mobile(value: str) -> str | None:
    mobile = normalize_digits(value).replace(" ", "").replace("-", "")
    if mobile.startswith("+98"):
        mobile = "0" + mobile[3:]
    elif mobile.startswith("98"):
        mobile = "0" + mobile[2:]
    if len(mobile) == 11 and mobile.startswith("09") and mobile.isdigit():
        return mobile
    return None