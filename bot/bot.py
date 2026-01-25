from aiogram import Bot, Dispatcher
from aiogram.filters import (
    CommandStart,
    Command,
)
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
import sys
from pathlib import Path

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.constants.endpoints import createUser, getUser, getUserRecords, getUsers
from helpers.http import backend_post, backend_get
from callbacks import CancelCallback, handle_cancel_callback
from config import BOT_TOKEN, ADDRESS, CONTACT
import logging
from utils.format_datetime import format_dt

logger = logging.getLogger(__name__)


def setup_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # /start
    @dp.message(CommandStart())
    async def start_handler(message: Message):
        user_id = message.from_user.id

        try:
            await backend_post(
                createUser,
                {
                    "user_id": message.from_user.id,
                    "name": message.from_user.full_name,
                    "username": message.from_user.username or "",
                },
            )
            logger.info(f"Пользователь с id={user_id} успешно сохранен или пропущен")

        except Exception as e:
            logger.error(
                f"Не удалось сохранить пользователя {message.from_user.id} {message.from_user.full_name} {message.from_user.username or ""}: {e}"
            )

        await message.answer(
            "👋 <b>Привет!</b> Я — Ваш персональный бот для записи на стрижку ✂️\n\n"
            "Здесь Вы можете:\n"
            "• 📅 Записаться на удобное время, нажав на кнопку «Записаться» слева от текстового поля\n"
            "• 👀 Просмотреть или отменить свои записи - /show\n"
            "• 📞 Получить контакт мастера - /contact\n\n"
            "Начнём? Просто используйте команды выше или введите «/» в текстовое поле для просмотра всех доступных команд 😉",
            parse_mode="HTML",
        )

        logger.info(f"Пользователь {message.from_user.id} запустил бота!")

    # /show
    @dp.message(Command(commands=["show"]))
    async def show_handler(message: Message):
        user_id = message.from_user.id

        logger.info(f"Пользователь {user_id} ввел /show")

        logger.info(f"Пользователь {user_id} запросил данные пользователя")
        try:
            res = await backend_get(f"{getUser}/{user_id}")
            user = res.json()
        except Exception as e:
            logger.error(f"Не удалось получить данные пользователя {user_id}")

        if not user:
            logger.info(
                f"Пользователь {user_id} не найден. Он будет записан в базу данных"
            )
            try:
                await backend_post(
                    createUser,
                    {
                        "user_id": message.from_user.id,
                        "name": message.from_user.full_name,
                        "username": message.from_user.username or "",
                    },
                )
                logger.info(f"Пользователь с id={user_id} успешно сохранен")
            except Exception as e:
                logger.error(
                    f"Не удалось сохранить пользователя {message.from_user.id} {message.from_user.full_name} {message.from_user.username or ""}: {e}"
                )
                await message.answer(
                    "Не удалось получить записи 😥\nПожалуйста, попробуйте позже"
                )
                return

        try:
            res = await backend_get(f"{getUsers}/{user_id}{getUserRecords}")
            records = res.json()
        except Exception as e:
            logger.info(f"Ошибка при получении записей пользователя {user_id}: {e}")
            await message.answer(
                "Не удалось получить записи 😥\nПожалуйста, попробуйте позже"
            )
            return

        if not records:
            await message.answer("У Вас нет активных записей")
            logger.info(f"У пользователя {user_id} нет активных записей")
            return

        count = 1
        for record_id, dt, name, service_name, address in records:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="❌ Отменить",
                            callback_data=CancelCallback(record_id=record_id).pack(),
                        )
                    ]
                ]
            )

            formatted_dt = format_dt(dt)

            await message.answer(
                f"📅 <b>Запись {count}</b>\n\n"
                f"👤 {name}\n"
                f"🕒 {formatted_dt}\n"
                f"✂️ {service_name}\n"
                f"📍 {address}\n",
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            count += 1

        logger.info(f"Пользователь {user_id} вывел список своих записей")

    @dp.callback_query(CancelCallback.filter())
    async def cancel_callback(query, callback_data: CancelCallback):
        await handle_cancel_callback(bot, query, callback_data)

    # /contact
    @dp.message(Command(commands=["contact"]))
    async def show_handler(message: Message):
        contact = CONTACT
        reply_text = (
            f"📞 Для уточнения деталей Вы можете обратиться к мастеру лично: {contact}"
        )

        await message.answer(reply_text)

        logger.info(
            f"Пользователь {message.from_user.id} отправил: {message.text} | Бот ответил: {reply_text}"
        )

    # Default
    @dp.message()
    async def all_messages(message: Message):
        reply_text = (
            "Извините, я Вас не понимаю 😥\n\n"
            "Вы можете ввести «/» в текстовое поле для просмотра всех доступных команд ☺️"
        )

        await message.answer(reply_text)

        logger.info(
            f"Пользователь {message.from_user.id} отправил: {message.text} | Бот ответил: {reply_text}"
        )

    return bot, dp
