import asyncio
from aiogram import Bot
from database.database import get_past_records, delete_record
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_cleanup_task = None
_cleanup_bot = None


async def send_thank_you_message(bot: Bot, user_id: int, name: str):
    """Отправляет сообщение благодарности клиенту"""
    try:
        msg = (
            "Спасибо за посещение, надеюсь Вам все понравилось! 😊\n\n"
            "Буду рад видеть Вас снова!"
        )
        await bot.send_message(user_id, msg)
        logger.info(
            f"Сообщение благодарности отправлено пользователю {user_id} ({name})"
        )
    except Exception as e:
        logger.error(
            f"Ошибка при отправке сообщения благодарности пользователю {user_id}: {e}"
        )


async def cleanup_past_records(bot: Bot):
    """Удаляет записи, которые прошли более 2 часов назад, и отправляет сообщение клиенту"""
    try:
        past_records = get_past_records(hours=2)

        if not past_records:
            logger.debug("Нет записей для удаления")
            return

        logger.info(f"Найдено {len(past_records)} записей для удаления")

        for record_id, user_id, name in past_records:
            try:
                await send_thank_you_message(bot, user_id, name)

                delete_record(record_id)
                logger.info(
                    f"Запись {record_id} удалена, сообщение отправлено пользователю {user_id}"
                )
            except Exception as e:
                logger.error(f"Ошибка при обработке записи {record_id}: {e}")

    except Exception as e:
        logger.error(f"Ошибка при очистке прошедших записей: {e}")


def start_cleanup_task(bot: Bot):
    """Запускает фоновую задачу для удаления прошедших записей каждые 30 минут"""
    global _cleanup_task, _cleanup_bot

    if _cleanup_task:
        return

    _cleanup_bot = bot

    async def loop():
        while True:
            try:
                await cleanup_past_records(_cleanup_bot)
            except Exception as e:
                logger.error(f"Ошибка в задаче очистки записей: {e}")

            await asyncio.sleep(30 * 60)

    _cleanup_task = asyncio.create_task(loop())
    logger.info("Задача очистки прошедших записей запущена")
