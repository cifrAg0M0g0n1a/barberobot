from datetime import datetime
import locale

locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")


def format_dt(dt_str: str) -> str:
    dt = datetime.fromisoformat(dt_str)
    return dt.strftime("%-d %B %Y, %H:%M")
