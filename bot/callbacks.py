import sys
from pathlib import Path

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from aiogram.types import CallbackQuery
from aiogram.filters.callback_data import (
    CallbackData,
)
from config import OWNER_ID
from utils.format_datetime import format_dt
from bot.constants.endpoints import deleteRecord, getRecordById
from helpers.http import backend_get, backend_delete

logger = logging.getLogger(__name__)


processing_records = set()


class CancelCallback(CallbackData, prefix="cancel"):
    record_id: int


async def handle_cancel_callback(
    bot, query: CallbackQuery, callback_data: CancelCallback
):
    if callback_data.record_id in processing_records:
        await query.answer("Уже обрабатывается… ⏳")
        return

    processing_records.add(callback_data.record_id)
    record_id = callback_data.record_id
    try:
        res = await backend_get(f"{getRecordById}/{record_id}")
        row = res.json()
    except Exception as e:
        logger.error(f"Не удалось получить запись с айди {record_id}")
        await query.message.edit_text("Не удалось отменить запись😥\nПопробуйте позже.")
        processing_records.remove(callback_data.record_id)
        return

    if not row:
        await query.message.edit_text("Запись уже удалена")
        logger.info(f"Запись {record_id} уже удалена")
        processing_records.remove(callback_data.record_id)
        return

    user_id, user_record_name, dt, username, service_name, address = row

    try:
        await backend_delete(f"{deleteRecord}/{record_id}")
    except Exception as e:
        logger.error(f"Ошибка при удалении записи {record_id}: {e}")
        await query.message.edit_text("Не удалось отменить запись😥\nПопробуйте позже.")
        processing_records.remove(callback_data.record_id)
        return

    formatted_dt = format_dt(dt)

    await query.message.edit_text(
        f"✅ Ваша запись на услугу «{service_name}» {formatted_dt} по адресу «{address}» отменена"
    )

    processing_records.remove(callback_data.record_id)

    try:
        await bot.send_message(
            OWNER_ID,
            f"💭 Клиент {user_record_name} отменил запись на {formatted_dt} по адресу: {address}\nУслуга: {service_name}\nТГ: @{username}",
        )
    except Exception as e:
        logger.error(f"Ошибка при уведомлении мастера: {e}")

    logger.info(f"Пользователь {user_id} отменил запись {record_id} на {dt}")
