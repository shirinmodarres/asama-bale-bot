from datetime import datetime, timedelta


def _gregorian_to_jalali(year: int, month: int, day: int) -> tuple[int, int, int]:
    gregorian_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    jalali_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]

    gy = year - 1600
    gm = month - 1
    gd = day - 1

    gregorian_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    gregorian_day_no += sum(gregorian_days_in_month[:gm])
    if gm > 1 and ((year % 4 == 0 and year % 100 != 0) or year % 400 == 0):
        gregorian_day_no += 1
    gregorian_day_no += gd

    jalali_day_no = gregorian_day_no - 79
    jalali_np = jalali_day_no // 12053
    jalali_day_no %= 12053

    jy = 979 + 33 * jalali_np + 4 * (jalali_day_no // 1461)
    jalali_day_no %= 1461

    if jalali_day_no >= 366:
        jy += (jalali_day_no - 1) // 365
        jalali_day_no = (jalali_day_no - 1) % 365

    jm = 0
    while jm < 11 and jalali_day_no >= jalali_days_in_month[jm]:
        jalali_day_no -= jalali_days_in_month[jm]
        jm += 1

    return jy, jm + 1, jalali_day_no + 1


def format_shamsi_datetime(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value

    tehran_time = parsed + timedelta(hours=3, minutes=30)
    jy, jm, jd = _gregorian_to_jalali(tehran_time.year, tehran_time.month, tehran_time.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d} {tehran_time.hour:02d}:{tehran_time.minute:02d}"