import random
import sys
from pathlib import Path

from backend.utils.generate_promo import generate_promo_code
from settings import DISCOUNT30, FREEFRIEND, FREESELF, LOSE

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from aiogram.types import CallbackQuery
from aiogram.filters.callback_data import (
    CallbackData,
)
from config import OWNER_ID
from utils.format_datetime import format_dt
from bot.constants.endpoints import deleteRecord, getRecordById, spinWheel, updateRecord
from bot.wheel import choose_prize
from bot.helpers.http import backend_get, backend_delete, backend_post, backend_patch

logger = logging.getLogger(__name__)


processing_records = set()

edit_record_state = {}


class CancelCallback(CallbackData, prefix="cancel"):
    record_id: int
    is_owner: bool


class EditCallback(CallbackData, prefix="edit"):
    record_id: int


class SpinCallback(CallbackData, prefix="spin"):
    action: str


async def handle_cancel_callback(
    bot, query: CallbackQuery, callback_data: CancelCallback
):
    if callback_data.record_id in processing_records:
        await query.answer("Уже обрабатывается… ⏳")
        return

    processing_records.add(callback_data.record_id)
    record_id = callback_data.record_id
    is_owner = callback_data.is_owner

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

    if is_owner:
        await query.message.edit_text(
            f"✅ Запись клиента {user_record_name} на услугу «{service_name}» {formatted_dt} по адресу «{address}» отменена"
        )
    else:
        await query.message.edit_text(
            f"✅ Ваша запись на услугу «{service_name}» {formatted_dt} по адресу «{address}» отменена"
        )

    processing_records.remove(callback_data.record_id)

    if is_owner:
        try:
            await bot.send_message(
                user_id,
                f"💭 Мастер отменил Вашу запись на {formatted_dt} по адресу: {address}. Для уточнения причины Вы можете связаться с мастером, получив контакты по команде /contact",
            )
        except Exception as e:
            logger.error(f"Ошибка при уведомлении пользователя об отмене мастером: {e}")

        logger.info(f"Мастер отменил запись {record_id} пользователя {user_id} на {dt}")
    else:
        try:
            await bot.send_message(
                OWNER_ID,
                f"💭 Клиент {user_record_name} отменил запись на {formatted_dt} по адресу: {address}\nУслуга: {service_name}\nТГ: @{username}",
            )
        except Exception as e:
            logger.error(f"Ошибка при уведомлении мастера: {e}")

        logger.info(f"Пользователь {user_id} отменил запись {record_id} на {dt}")


async def handle_edit_callback(bot, query: CallbackQuery, callback_data: EditCallback):
    """Мастер нажал «Редактировать» — просим ввести новое время"""
    if query.from_user.id != OWNER_ID:
        await query.answer("Только мастер может редактировать запись", show_alert=True)
        return

    record_id = callback_data.record_id

    try:
        res = await backend_get(f"{getRecordById}/{record_id}")
        row = res.json()
    except Exception as e:
        logger.error(f"Не удалось получить запись {record_id}: {e}")
        await query.answer("Ошибка загрузки записи", show_alert=True)
        return

    if not row:
        await query.answer("Запись уже удалена", show_alert=True)
        return

    edit_record_state[query.from_user.id] = record_id

    await query.message.edit_text(
        "✏️ Введите новые дату и время в формате:\n"
        "<b>ДД.ММ.ГГГГ ЧЧ:ММ</b>\n\n"
        "Например: <code>15.02.2026 14:30</code>\n\n"
        "Можно указать любое удобное время",
        parse_mode="HTML",
    )
    await query.answer()


def parse_datetime_input(text: str):
    """
    Парсит дату/время из сообщения.
    Принимает: ДД.ММ.ГГГГ ЧЧ:ММ или ДД.ММ.ГГГГ ЧЧ:ММ:СС или YYYY-MM-DD HH:MM.
    Возвращает (datetime, None) или (None, error_message)
    """
    from datetime import datetime

    text = text.strip()
    if "." in text and " " in text:
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            return None, "Укажите дату и время через пробел, например: 15.02.2026 14:30"
        date_part, time_part = parts
        try:
            day, month, year = map(int, date_part.split("."))
            if len(time_part) == 5:  # HH:MM
                hour, minute = map(int, time_part.split(":"))
                second = 0
            elif len(time_part) >= 8:  # HH:MM:SS
                t = time_part.split(":")
                hour, minute = int(t[0]), int(t[1])
                second = int(t[2]) if len(t) > 2 else 0
            else:
                return None, "Время в формате ЧЧ:ММ или ЧЧ:ММ:СС"
            dt = datetime(year, month, day, hour, minute, second)
            return dt, None
        except (ValueError, IndexError) as e:
            return None, "Неверный формат. Пример: 15.02.2026 14:30"
    if "-" in text and " " in text:
        try:
            if len(text) == 16:  # YYYY-MM-DD HH:MM
                dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
            else:
                dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            return dt, None
        except ValueError:
            return None, "Неверный формат. Пример: 15.02.2026 14:30"
    return None, "Укажите дату и время, например: 15.02.2026 14:30"


async def handle_edit_datetime_message(bot, message, record_id: int, new_dt_str: str):
    """
    Обновляет время записи по API, уведомляет клиента, сбрасывает состояние
    """
    from backend.utils.format_datetime import format_dt

    dt, err = parse_datetime_input(new_dt_str)
    if err:
        await message.answer(f"❌ {err}")
        return

    dt_str_api = dt.strftime("%Y-%m-%d %H:%M")
    if dt.second:
        dt_str_api += f":{dt.second:02d}"
    else:
        dt_str_api += ":00"

    try:
        res = await backend_patch(
            f"{updateRecord}/{record_id}",
            {"datetime": dt_str_api},
        )
        res.raise_for_status()
    except Exception as e:
        logger.error(f"Ошибка при обновлении записи {record_id}: {e}")
        await message.answer("Не удалось обновить запись. Попробуйте позже")
        edit_record_state.pop(message.from_user.id, None)
        return

    edit_record_state.pop(message.from_user.id, None)

    try:
        res = await backend_get(f"{getRecordById}/{record_id}")
        row = res.json()
    except Exception:
        row = None

    formatted = format_dt(dt_str_api)
    await message.answer(f"✅ Дата и время записи изменены на {formatted}")

    if row:
        user_id, name, _, _, service_name, address = row
        try:
            await bot.send_message(
                user_id,
                f"✏️ Мастер изменил дату и время вашей записи на <b>{formatted}</b>\n"
                f"Услуга: {service_name}\nАдрес: {address}",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Ошибка при уведомлении клиента {user_id}: {e}")

    logger.info(f"Мастер изменил дату и время записи {record_id} на {dt_str_api}")


async def handle_spin_callback(bot, query: CallbackQuery, callback_data: SpinCallback):
    user_id = query.from_user.id

    if user_id in processing_records:
        await query.answer("Уже обрабатывается… ⏳")
        return

    processing_records.add(user_id)

    try:
        res = await backend_get(f"{spinWheel}/check/{user_id}")
        res.raise_for_status()
        data = res.json()
        if data.get("has_spin", False):
            await query.answer("Вы уже крутили колесо 😉", show_alert=True)
            processing_records.remove(user_id)
            return
    except Exception as e:
        logger.error(
            f"При попытке пользователем {user_id} проверить, не использован ли спин повторно, произошла ошибка: {e}"
        )
        await query.message.edit_text(
            "😬 Произошла ошибка, попробуйте позже", parse_mode="HTML"
        )
        processing_records.remove(user_id)
        return

    prize_key = choose_prize()

    promo_code = None
    text = ""

    if prize_key == LOSE:
        text = "😔 Увы, в этот раз без приза"
    else:
        promo_code = generate_promo_code(prize_key)

        if prize_key == DISCOUNT30:
            text = (
                "🎉 <b>Поздравляем!</b>\n\n"
                "Вы выиграли <b>скидку 30%</b> ✂️\n\n"
                f"🎫 <b>Промокод:</b> <code>{promo_code}</code>\n"
                "Используйте его при записи"
            )

        elif prize_key == FREEFRIEND:
            text = (
                "🎉 <b>Поздравляем!</b>\n\n"
                "🎁 <b>Бесплатная стрижка для друга</b>\n\n"
                f"🎫 <b>Промокод:</b> <code>{promo_code}</code>\n"
                "⚠️ Вы не можете использовать его сами"
            )

        elif prize_key == FREESELF:
            text = (
                "👑 <b>ДЖЕКПОТ!</b>\n\n"
                "✂️ <b>Бесплатная стрижка для вас</b>\n\n"
                f"🎫 <b>Промокод:</b> <code>{promo_code}</code>\n"
                "Используйте его при записи"
            )
        else:
            text = "Что-то пошло не так 😅\nПожалуйста, попробуйте позже"

    try:
        res = await backend_post(
            f"{spinWheel}/{user_id}",
            {
                "prize_type": prize_key,
                "promo_code": promo_code,
            },
        )
        res.raise_for_status()
    except Exception as e:
        logger.error(
            f"При сохранении результата спина у пользователя {user_id} произошла ошибка: {e}"
        )
        await query.message.edit_text(
            "😬 Произошла ошибка при сохранении результата, попробуйте позже",
            parse_mode="HTML",
        )
        processing_records.remove(user_id)
        return

    processing_records.remove(user_id)
    await query.message.edit_text(text, parse_mode="HTML")
    await query.answer()
