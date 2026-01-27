from datetime import datetime
import locale

RUSSIAN_MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

_russian_locale_available = False
try:
    locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
    _russian_locale_available = True
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "ru_RU")
        _russian_locale_available = True
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, "ru_RU.utf8")
            _russian_locale_available = True
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, "ru")
                _russian_locale_available = True
            except locale.Error:
                pass


def format_dt(dt_str: str) -> str:
    dt = datetime.fromisoformat(dt_str)

    if _russian_locale_available:
        try:
            return dt.strftime("%-d %B %Y, %H:%M")
        except ValueError:
            return dt.strftime("%d %B %Y, %H:%M")

    day = dt.day
    month = RUSSIAN_MONTHS[dt.month]
    year = dt.year
    hour = dt.hour
    minute = dt.minute

    return f"{day} {month} {year}, {hour:02d}:{minute:02d}"
