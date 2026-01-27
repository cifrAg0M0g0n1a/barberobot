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
from bot.constants.endpoints import deleteRecord, getRecordById, spinWheel
from bot.wheel import choose_prize
from bot.helpers.http import backend_get, backend_delete, backend_post

logger = logging.getLogger(__name__)


processing_records = set()


class CancelCallback(CallbackData, prefix="cancel"):
    record_id: int
    is_owner: bool


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
