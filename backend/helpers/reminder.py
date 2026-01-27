from datetime import datetime, timedelta
import sys
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import get_user_records_for_reminder, mark_reminder_sent
from backend.utils.format_datetime import format_dt
from aiogram import Bot
from settings import TIMEZONE
from backend.utils.logger import get_logger

logger = get_logger(__name__)

scheduler = AsyncIOScheduler(timezone=TIMEZONE)


async def send_reminder(
    bot: Bot,
    user_id: int,
    record_id: int,
    dt_str: str,
    name: str,
    service: str,
    price: int,
    address: str,
):
    """
    Отправляет напоминание клиенту и помечает его в БД
    """
    try:
        msg = (
            f"<b>Напоминание о записи</b>\n\n"
            f"👤 {name}\n"
            f"🗓 {format_dt(dt_str)}\n"
            f"✂️ {service}\n"
            f"💸 {price}\n"
            f"📍 {address}\n\n"
            "Жду Вас через 2 часа! 😉"
        )
        await bot.send_message(user_id, msg, parse_mode="HTML")
        mark_reminder_sent(record_id)
        logger.info(
            f"Напоминание отправлено пользователю {user_id}, запись {record_id}"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания {record_id}: {e}")


async def schedule_reminders(bot: Bot):
    """
    Проходит по всем будущим записям и ставит job на 2 часа до записи
    """
    try:
        records = get_user_records_for_reminder()
    except Exception as e:
        logger.error(f"Не удалось запросить записи для напоминания. Ошибка: {e}")
        return

    now = datetime.now(TIMEZONE)

    for record_id, user_id, dt_str, name, service, price, address in records:
        try:
            if len(dt_str) == 16:  # "YYYY-MM-DD HH:MM"
                dt_str = dt_str + ":00"

            record_dt = datetime.fromisoformat(dt_str)
            if record_dt.tzinfo is None:
                record_dt = record_dt.replace(tzinfo=TIMEZONE)

            reminder_time = record_dt - timedelta(hours=2)

            if reminder_time <= now:
                continue

            trigger = DateTrigger(run_date=reminder_time)
            scheduler.add_job(
                send_reminder,
                trigger=trigger,
                args=(bot, user_id, record_id, dt_str, name, service, price, address),
                id=f"reminder_{record_id}",
                replace_existing=True,
            )
            logger.info(f"Напоминание для {user_id} записано на {reminder_time}")
        except Exception as e:
            logger.error(
                f"Ошибка при планировании напоминания для записи {record_id}: {e}"
            )


async def schedule_one_reminder(
    bot: Bot,
    record_id: int,
    user_id: int,
    dt_str: str,
    name: str,
    service: str,
    price: int,
    address: str,
):
    try:
        if len(dt_str) == 16:  # "YYYY-MM-DD HH:MM"
            dt_str = dt_str + ":00"

        record_dt = datetime.fromisoformat(dt_str)
        if record_dt.tzinfo is None:
            record_dt = record_dt.replace(tzinfo=TIMEZONE)

        reminder_time = record_dt - timedelta(hours=2)
        now = datetime.now(TIMEZONE)

        if reminder_time <= now:
            logger.warning(
                f"Напоминание для записи {record_id} не может быть запланировано: "
                f"время напоминания ({reminder_time}) уже прошло"
            )
            return

        scheduler.add_job(
            send_reminder,
            trigger=DateTrigger(run_date=reminder_time),
            args=(bot, user_id, record_id, dt_str, name, service, price, address),
            id=f"reminder_{record_id}",
            replace_existing=True,
        )

        logger.info(
            f"[REMINDER] Запланировано для user={user_id}, record={record_id} на {reminder_time}"
        )
    except Exception as e:
        logger.error(f"Ошибка при планировании напоминания для записи {record_id}: {e}")
