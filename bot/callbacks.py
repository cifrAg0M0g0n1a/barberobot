import logging
from aiogram.types import CallbackQuery  # pyright: ignore[reportMissingImports]
from aiogram.filters.callback_data import (  # pyright: ignore[reportMissingImports]
    CallbackData,
)
from config import OWNER_ID
from database.database import get_record, delete_record
from utils.format_datetime import format_dt

logger = logging.getLogger(__name__)


class CancelCallback(CallbackData, prefix="cancel"):
    record_id: int


async def handle_cancel_callback(
    bot, query: CallbackQuery, callback_data: CancelCallback
):
    record_id = callback_data.record_id

    row = get_record(record_id)
    if not row:
        await query.message.edit_text("Запись уже удалена")
        logger.info(f"Запись {record_id} уже удалена")
        return

    user_id, user_record_name, dt, username, service_name = row

    try:
        delete_record(record_id)
    except Exception as e:
        logger.error(f"Ошибка при удалении записи {record_id}: {e}")
        await query.message.edit_text("Не удалось отменить запись😥\nПопробуйте позже.")
        return

    formatted_dt = format_dt(dt)

    await query.message.edit_text(
        f"✅ Ваша запись на услугу «{service_name}» {formatted_dt} отменена"
    )

    try:
        await bot.send_message(
            OWNER_ID,
            f"💭 Клиент {user_record_name} отменил запись на {formatted_dt}\nУслуга: {service_name}\nТГ: @{username}",
        )
    except Exception as e:
        logger.error(f"Ошибка при уведомлении мастера: {e}")

    logger.info(f"Пользователь {user_id} отменил запись {record_id} на {dt}")
