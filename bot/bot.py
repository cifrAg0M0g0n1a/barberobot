from aiogram import Bot, Dispatcher  # pyright: ignore[reportMissingImports]
from aiogram.filters import (  # pyright: ignore[reportMissingImports]
    CommandStart,
    Command,
)
from aiogram.types import (  # pyright: ignore[reportMissingImports]
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from bot.callbacks import CancelCallback, handle_cancel_callback
from config import BOT_TOKEN, ADDRESS, CONTACT
import logging
from database.database import get_user_records, add_user_if_not_exists
from utils.format_datetime import format_dt

logger = logging.getLogger(__name__)


def setup_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # /start
    @dp.message(CommandStart())
    async def start_handler(message: Message):
        try:
            add_user_if_not_exists(
                user_id=message.from_user.id,
                name=message.from_user.full_name,
                username=message.from_user.username or "",
            )
            logger.info(f"Пользователь с id={message.from_user.id} успешно сохранен")
        except Exception as e:
            logger.error(
                f"Не удалось сохранить пользователя {message.from_user.id}: {e}"
            )

        await message.answer(
            "👋 Привет! Я — Ваш персональный бот для записи на стрижку ✂️\n\n"
            "Здесь Вы можете:\n"
            "• 📅 Записаться на удобное время (/record)\n"
            "• 👀 Просмотреть свои записи (/show)\n"
            "• ❌ И тут же отменить запись! (/show)\n"
            "• 📞 А также получить контакт мастера (/contact)\n\n"
            "Начнём? Просто используйте команды выше или нажмите на бургер-кнопку, расположенную слева от текстового поля 😉"
        )

        logger.info(f"Пользователь {message.from_user.id} запустил бота!")

    # /show
    @dp.message(Command(commands=["show"]))
    async def show_handler(message: Message):
        user_id = message.from_user.id

        logger.info(f"Пользователь {user_id} ввел /show")

        try:
            records = get_user_records(user_id)
        except Exception as e:
            logger.info(f"Ошибка при получении записей пользователя {user_id}: {e}")
            await message.answer("Не удалось получить записи😥")
            return

        if not records:
            await message.answer("У вас нет активных записей")
            logger.info(f"У пользователя {user_id} нет активных записей")
            return

        count = 1
        for record_id, dt, name, service_name in records:
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
            address = ADDRESS

            await message.answer(
                f"📅 <b>Запись {count}</b>\n\n"
                f"👤 {name}\n"
                f"🕒 {formatted_dt}\n"
                f"✂️ {service_name}\n"
                f"📍 {address}",
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
            "Извините, я вас не понимаю 😥\n\n"
            "Все доступные команды можно посмотреть, нажав на бургер-кнопку слева от текстового поля ☺️"
        )

        await message.answer(reply_text)

        logger.info(
            f"Пользователь {message.from_user.id} отправил: {message.text} | Бот ответил: {reply_text}"
        )

    return bot, dp
