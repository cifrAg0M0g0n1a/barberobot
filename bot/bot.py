from aiogram import Bot, Dispatcher
from aiogram.filters import (
    CommandStart,
    Command,
)
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BufferedInputFile,
)
import sys
from pathlib import Path
from openpyxl import Workbook
from io import BytesIO

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.constants.endpoints import (
    createUser,
    getUser,
    getUserRecords,
    getUsers,
    getAllRecords,
)
from bot.helpers.http import backend_post, backend_get
from bot.callbacks import (
    CancelCallback,
    EditCallback,
    SpinCallback,
    edit_record_state,
    handle_cancel_callback,
    handle_edit_callback,
    handle_edit_datetime_message,
    handle_spin_callback,
)
from config import BOT_TOKEN, CONTACT, OWNER_ID
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
            "• 📞 Получить контакт мастера - /contact\n"
            "• 🎡 Прокрутить колесо фортуны - /spin\n\n"
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
        user = None
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
            if user_id == OWNER_ID:
                res = await backend_get(f"{getAllRecords}/{user_id}")
            else:
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

        is_owner = user_id == OWNER_ID
        count = 1

        if user_id == OWNER_ID:
            wb = Workbook()
            ws = wb.active
            ws.title = "Записи"

            ws.append([
                "№",
                "Клиент",
                "Телефон",
                "Дата и время",
                "Услуга",
                "Цена",
                "Адрес",
                "Telegram"
            ])

            count = 1

            for record_id, dt, name, service_name, address, phone, username, price in records:
                formatted_dt = format_dt(dt)

                ws.append([
                    count,
                    name,
                    phone,
                    formatted_dt,
                    service_name,
                    price,
                    address,
                    f"@{username}" if username else "—"
                ])

                count += 1

            file_stream = BytesIO()
            wb.save(file_stream)
            file_stream.seek(0)

            file = BufferedInputFile(
                file_stream.read(),
                filename="records.xlsx"
            )

            await message.answer_document(
                file,
                caption="📊 Все записи"
            )
        else:
            for record_id, dt, name, service_name, address, price in records:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="❌ Отменить",
                                callback_data=CancelCallback(
                                    record_id=record_id,
                                    is_owner=is_owner,
                                ).pack(),
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
                    f"💸 {price} ₽\n"
                    f"📍 {address}\n",
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
                count += 1

        logger.info(f"Пользователь {user_id} вывел список своих записей")

    @dp.callback_query(CancelCallback.filter())
    async def cancel_callback(query, callback_data: CancelCallback):
        await handle_cancel_callback(bot, query, callback_data)

    @dp.callback_query(EditCallback.filter())
    async def edit_callback(query, callback_data: EditCallback):
        await handle_edit_callback(bot, query, callback_data)

    @dp.message(lambda m: m.from_user and m.from_user.id in edit_record_state)
    async def edit_datetime_handler(message: Message):
        record_id = edit_record_state.get(message.from_user.id)
        if record_id is None:
            return
        await handle_edit_datetime_message(bot, message, record_id, message.text or "")

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

    @dp.message(Command(commands="spin"))
    async def spin_handler(message: Message):
        user_id = message.from_user.id
        logger.info(f"Пользователь {user_id} ввел /spin")

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎡 Крутануть",
                        callback_data=SpinCallback(action="start").pack(),
                    )
                ]
            ]
        )

        text = (
            "🎡 <b>Колесо фортуны</b>\n\n"
            "Вы можете испытать удачу <b>ТОЛЬКО ОДИН РАЗ</b>\n\n"
            "<b>Возможные призы:</b>\n"
            "❌ Ничего\n"
            "💸 Скидка <b>30%</b>\n"
            "🎁 Бесплатная стрижка <i>другу</i>\n"
            "👑 Бесплатная стрижка <i>для вас</i>\n\n"
            "Нажмите кнопку ниже, чтобы крутануть колесо 👇"
        )

        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    @dp.callback_query(SpinCallback.filter())
    async def spin_callback(query, callback_data: SpinCallback):
        await handle_spin_callback(bot, query, callback_data)

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
