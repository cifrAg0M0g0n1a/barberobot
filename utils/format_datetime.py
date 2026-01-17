from datetime import datetime
import locale

locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")


def format_dt(dt_str: str) -> str:
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    return dt.strftime("%-d %B %Y, %H:%M")
