from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from database.database import (
    delete_record,
    get_record,
    get_slots_for_date,
    get_service,
    add_record_cut,
    add_user_if_not_exists,
    get_user_records,
    get_user,
)
from settings import WORK_START, WORK_END, TIMEZONE, SERVICE_DURATION_MIN
from datetime import date, datetime, timedelta
from config import ADDRESS
from pathlib import Path
from backend.utils.logger import get_logger
from backend.utils.format_datetime import format_dt
from aiogram import Bot
from config import BOT_TOKEN, OWNER_ID
import asyncio


bot = Bot(token=BOT_TOKEN)
router = APIRouter()
logger = get_logger(__name__)


timezone = TIMEZONE

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    logger.info("Открыта страница записи")
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/address")
async def get_address():
    logger.info("Получен адрес")
    return {"address": ADDRESS}


@router.get("/service")
async def get_service_info():
    """
    Возвращает данные об услуге по имени
    """
    logger.info("Получение услуги...")
    service = get_service("Стрижка")
    if not service:
        logger.error("Услуга не найдена")
        raise HTTPException(status_code=404, detail="Service not found")
    logger.info("Услуга успешно получена")
    return {"name": service["name"], "price": service["price"]}


@router.get("/slots")
async def get_slots(date: str):
    """
    Возвращает слоты для выбранной даты.
    Формат date: 'YYYY-MM-DD'
    """
    logger.info("Получение слотов времени по дате...")

    try:
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        logger.error("Неверный формат даты")
        raise HTTPException(status_code=400, detail="Invalid date format")

    logger.info("Запрос слотов из базы данных")
    existing = get_slots_for_date(selected_date)

    start_hour, start_min = map(int, WORK_START.split(":"))
    end_hour, end_min = map(int, WORK_END.split(":"))
    slots = []

    current = datetime.combine(selected_date, datetime.min.time()).replace(
        hour=start_hour, minute=start_min
    )
    end_time = current.replace(hour=end_hour, minute=end_min)

    while current + timedelta(minutes=SERVICE_DURATION_MIN) <= end_time:
        slot_time = current.strftime("%H:%M")
        slots.append({"time": slot_time, "available": slot_time not in existing})
        current += timedelta(minutes=SERVICE_DURATION_MIN)

    logger.info(f"Вывод слотов: {slots}")
    return slots


@router.post("/add_record")
async def add_record(request: Request):
    payload = await request.json()
    name = payload.get("name")
    phone = payload.get("phone")
    date_str = payload.get("date")
    time_str = payload.get("time")
    userId = payload.get("userId")
    username = payload.get("username")
    address = payload.get("address")

    logger.info("Старт записи...")

    if not all([name, phone, date_str, time_str, userId]):
        logger.error("Утерянные поля")
        raise HTTPException(status_code=400, detail="Missing fields")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        time_obj = datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        logger.error("Неверный формат даты или времени")
        raise HTTPException(status_code=400, detail="Неверный формат даты или времени")

    if date_obj <= date.today():
        raise HTTPException(
            status_code=400, detail="Нельзя записаться на прошедшую или текущую дату"
        )

    logger.info("Запрос услуги...")
    service = get_service("Стрижка")
    if not service:
        logger.error("Услуга не найдена")
        raise HTTPException(status_code=404, detail="Service not found")

    existing_slots = get_slots_for_date(date_obj)
    if time_obj.strftime("%H:%M") in existing_slots:
        dt_obj = datetime.fromisoformat(date_str)
        formatted_date = dt_obj.strftime("%-d %B %Y")
        logger.warning(
            f"Пользователь {userId} {name} {username} попытался записаться на слот {time_str} на {formatted_date}, но данный слот уже занят"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Слот {time_str} на {formatted_date} уже занят. Пожалуйста, выберите другое время",
        )

    logger.info(f"Запрос добавления записи для юзера {userId}...")
    add_record_cut(
        user_id=userId,
        datetime_obj=datetime.combine(date_obj, time_obj),
        service_id=service["id"],
        name=name,
        phone=phone,
        address=address,
    )
    logger.info(
        f"Отправленные поля: user_id={userId}, datetime={datetime.combine(date_obj, time_obj)}, service_id={service["id"]}, name={name}, phone={phone}, address={address}"
    )

    msg = ""

    if username:
        msg = (
            f"<b>Новая запись!</b>\n\n"
            f"👤 <i>Клиент</i>: {name}\n"
            f"📞 <i>Телефон</i>: {phone}\n"
            f"🗓 <i>Дата и время</i>: {format_dt(f"{date_str} {time_str}")}\n"
            f"✂️ <i>Услуга</i>: {service['name']}\n"
            f"📍 <i>Адрес</i>: {address}\n"
            f"💬 <i>Telegram</i>: @{username}"
        )
    else:
        msg = (
            f"<b>Новая запись!</b>\n\n"
            f"👤 <i>Клиент</i>: {name}\n"
            f"📞 <i>Телефон</i>: {phone}\n"
            f"🗓 <i>Дата и время</i>: {format_dt(f"{date_str} {time_str}")}\n"
            f"✂️ <i>Услуга</i>: {service['name']}\n"
            f"📍 <i>Адрес</i>: {address}\n"
            f"💬 <i>Telegram</i>: юзернейм отсутствует"
        )

    try:
        logger.info(f"Отправка записи мастеру для пользователя: {userId}...")
        asyncio.create_task(
            bot.send_message(
                OWNER_ID,
                msg,
                parse_mode="HTML",
            )
        )
    except Exception as e:
        logger.error(
            f"Ошибка при отправки записи мастеру для пользователя: {userId}. Ошибка: {e}"
        )

    logger.info("Запись успешно добалена")
    return {"message": "Запись успешно добавлена!"}


@router.post("/create-user")
async def create_user(payload: dict):
    user_id = payload.get("user_id")
    name = payload.get("name")
    username = payload.get("username", "")

    if not user_id or not name:
        logger.error("Не удалось получить переданные данные")
        raise HTTPException(status_code=400, detail="Missing fields")

    logger.info(f"Создание пользователя {user_id} {name} {username}...")

    add_user_if_not_exists(
        user_id=user_id,
        name=name,
        username=username,
    )

    logger.info(f"Пользователь {user_id} {name} {username} успешно создан или пропущен")
    return {"status": "ok"}


@router.get("/get-user/{user_id}")
async def create_user(user_id: int):
    logger.info(f"Запрос юзера c айди {user_id}...")

    user = get_user(user_id)

    logger.info(f"Юзер успешно получен: {user}")
    return user


@router.get("/users/{user_id}/records")
async def get_user_records_api(user_id: int):
    logger.info(f"Запрос записей юзера c айди {user_id}...")
    records = get_user_records(user_id)

    logger.info(f"Записи юзера {user_id} успешно получены: {records}")
    return records


@router.get("/get-record/{record_id}")
async def get_record_by_id(record_id: int):
    logger.info(f"Запрос записи с айди {record_id}...")
    record = get_record(record_id)

    logger.info(f"Запись с айди {record_id} успешна получена: {record}")
    return record


@router.delete("/delete-record/{record_id}")
async def get_record_by_id(record_id: int):
    logger.info(f"Удаление записи с айди {record_id}...")
    delete_record(record_id)

    logger.info(f"Запись с айди {record_id} успешна удалена")
    return {"status": "ok"}
