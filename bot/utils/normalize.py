def normalize_digits(value: str) -> str:
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"

    result = str(value)
    for p, e in zip(persian_digits, english_digits):
        result = result.replace(p, e)
    for a, e in zip(arabic_digits, english_digits):
        result = result.replace(a, e)
    return result.strip()