from sched import scheduler
from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from backend.helpers.reminder import schedule_one_reminder, cancel_reminder_job
from database.database import (
    delete_record,
    get_all_records,
    get_record,
    get_slots_for_date,
    get_service,
    get_service_by_id,
    get_all_services,
    add_record_cut,
    add_user_if_not_exists,
    get_user_records,
    get_user,
    has_user_spin,
    save_spin,
    get_promo_code,
    use_promo_code,
    update_record_datetime,
)
from settings import (
    WORK_START,
    WORK_END,
    TIMEZONE,
    SERVICE_DURATION_MIN,
    DISCOUNT30,
    FREEFRIEND,
    FREESELF,
)
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


@router.get("/services")
async def get_services_list():
    """Возвращает список всех услуг (id, name, price)."""
    logger.info("Получение списка услуг...")
    services = get_all_services()
    if not services:
        logger.error("Услуги не найдены")
        raise HTTPException(status_code=404, detail="Services not found")
    return [{"id": s["id"], "name": s["name"], "price": s["price"]} for s in services]


@router.get("/service")
async def get_service_info(service_id: int | None = None):
    """
    Возвращает данные об одной услуге: по service_id (query ?service_id=1) или первую по умолчанию.
    """
    logger.info("Получение услуги...")
    if service_id is not None:
        service = get_service_by_id(service_id)
    else:
        services = get_all_services()
        service = services[0] if services else None
    if not service:
        logger.error("Услуга не найдена")
        raise HTTPException(status_code=404, detail="Service not found")
    logger.info("Услуга успешно получена")
    return {"id": service["id"], "name": service["name"], "price": service["price"]}


@router.get("/slots")
async def get_slots(date: str):
    """
    Возвращает слоты для выбранной даты (общие для всех услуг — одно время = одна запись).
    Формат date: 'YYYY-MM-DD'.
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
    price = payload.get("price")
    promo_code = payload.get("promo_code")

    logger.info("Старт записи...")

    promo_info = None
    final_price = price
    if promo_code:
        promo_info = get_promo_code(promo_code)
        if not promo_info:
            raise HTTPException(status_code=400, detail="Промокод не найден")

        (
            promo_id,
            _,
            prize_type,
            discount_percent,
            owner_user_id,
            allow_owner,
            used,
            _,
            _,
        ) = promo_info

        if used:
            raise HTTPException(status_code=400, detail="Промокод уже использован")

        if userId == owner_user_id and allow_owner == 0:
            raise HTTPException(
                status_code=400, detail="Вы не можете использовать этот промокод"
            )

        if prize_type == FREESELF:
            final_price = 0
        elif prize_type == FREEFRIEND:
            final_price = 0
        elif prize_type == DISCOUNT30 and discount_percent:
            final_price = int(price * (1 - discount_percent / 100))

    if not all([name, phone, date_str, time_str, userId]):
        logger.error("Утерянные поля")
        raise HTTPException(status_code=400, detail="Missing fields")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        time_obj = datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        logger.error("Неверный формат даты или времени")
        raise HTTPException(status_code=400, detail="Неверный формат даты или времени")

    if date_obj < date.today():
        logger.error("Нельзя записаться на прошедшую дату")
        raise HTTPException(
            status_code=400, detail="Нельзя записаться на прошедшую дату"
        )

    service_id = payload.get("service_id")
    if not service_id:
        logger.error("Не указана услуга (service_id)")
        raise HTTPException(status_code=400, detail="Укажите услугу")

    logger.info("Запрос услуги...")
    service = get_service_by_id(int(service_id))
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
    recordId = add_record_cut(
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

    if promo_code and promo_info:
        promo_used = use_promo_code(promo_code, userId)
        if not promo_used:
            logger.warning(
                f"Не удалось использовать промокод {promo_code} для пользователя {userId}"
            )
        else:
            logger.info(
                f"Промокод {promo_code} успешно использован пользователем {userId}"
            )

    await schedule_one_reminder(
        bot=bot,
        record_id=recordId,
        user_id=userId,
        dt_str=f"{date_str} {time_str}",
        name=name,
        service=service["name"],
        price=final_price,
        address=address,
    )

    msg = ""

    promo_text = ""
    if promo_code and promo_info:
        _, _, prize_type, _, _, _, _, _, _ = promo_info
        if prize_type == FREESELF:
            promo_text = "\n🎫 <i>Промокод</i>: Бесплатная стрижка"
        elif prize_type == FREEFRIEND:
            promo_text = "\n🎫 <i>Промокод</i>: Бесплатная стрижка другу"
        elif prize_type == DISCOUNT30:
            promo_text = f"\n🎫 <i>Промокод</i>: Скидка 30% (цена: {final_price} ₽)"

    if username != "":
        msg = (
            f"<b>Новая запись!</b>\n\n"
            f"👤 <i>Клиент</i>: {name}\n"
            f"📞 <i>Телефон</i>: {phone}\n"
            f"🗓 <i>Дата и время</i>: {format_dt(f"{date_str} {time_str}")}\n"
            f"✂️ <i>Услуга</i>: {service['name']}\n"
            f"📍 <i>Адрес</i>: {address}\n"
            f"💸 <i>Итоговая цена</i>: {final_price} ₽\n"
            f"💬 <i>Telegram</i>: @{username}"
            f"{promo_text}"
        )
    else:
        msg = (
            f"<b>Новая запись!</b>\n\n"
            f"👤 <i>Клиент</i>: {name}\n"
            f"📞 <i>Телефон</i>: {phone}\n"
            f"🗓 <i>Дата и время</i>: {format_dt(f"{date_str} {time_str}")}\n"
            f"✂️ <i>Услуга</i>: {service['name']}\n"
            f"📍 <i>Адрес</i>: {address}\n"
            f"💸 <i>Итоговая цена</i>: {final_price} ₽\n"
            f"💬 <i>Telegram</i>: юзернейм отсутствует"
            f"{promo_text}"
        )

    try:
        logger.info(
            f"Отправка записи мастеру для пользователя: {userId} {name} {username}..."
        )
        asyncio.create_task(
            bot.send_message(
                OWNER_ID,
                msg,
                parse_mode="HTML",
            )
        )
    except Exception as e:
        logger.error(
            f"Ошибка при отправки записи мастеру для пользователя: {userId} {name} {username}. Ошибка: {e}"
        )

    try:
        logger.info(f"Отправка записи пользователю: {userId} {name} {username}...")
        promo_user_text = ""
        if promo_code and promo_info:
            _, _, prize_type, _, _, _, _, _, _ = promo_info
            if prize_type == FREESELF:
                promo_user_text = "\n🎁 <b>Бесплатная стрижка по промокоду!</b>"
            elif prize_type == FREEFRIEND:
                promo_user_text = "\n🎁 <b>Бесплатная стрижка по промокоду!</b>"
            elif prize_type == DISCOUNT30:
                promo_user_text = (
                    f"\n💸 <b>Применена скидка 30%!</b> Итоговая цена: {final_price} ₽"
                )

        asyncio.create_task(
            bot.send_message(
                userId,
                (
                    f"<b>Вы успешно записались на стрижку! За два часа до выбранного времени я пришлю уведомление 😉</b>\n\n"
                    f"🗓 <i>Дата и время</i>: {format_dt(f"{date_str} {time_str}")}\n"
                    f"✂️ <i>Услуга</i>: {service['name']}\n"
                    f"📍 <i>Адрес</i>: {address}\n"
                    f"{promo_user_text}"
                ),
                parse_mode="HTML",
            )
        )
    except Exception as e:
        logger.error(
            f"Ошибка при отправки записи пользователю: {userId} {name} {username}. Ошибка: {e}"
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
async def get_user_data(user_id: int):
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


@router.get("/get-all-records/{user_id}")
async def get_all_records_api(user_id: int):
    logger.info(f"Запрос всех записей юзером {user_id}...")
    records = get_all_records()

    logger.info(f"Все записи юзером {user_id} успешно получены: {records}")
    return records


@router.get("/get-record/{record_id}")
async def get_record_by_id(record_id: int):
    logger.info(f"Запрос записи с айди {record_id}...")
    record = get_record(record_id)

    logger.info(f"Запись с айди {record_id} успешна получена: {record}")
    return record


@router.delete("/delete-record/{record_id}")
async def delete_record_by_id(record_id: int):
    logger.info(f"Удаление записи с айди {record_id}...")
    cancel_reminder_job(record_id)
    delete_record(record_id)

    logger.info(f"Запись с айди {record_id} успешна удалена")
    return {"status": "ok"}


@router.patch("/update-record/{record_id}")
async def update_record_by_id(record_id: int, request: Request):
    """Обновляет дату и время записи. Тело: {"datetime": "YYYY-MM-DD HH:MM"} или {"datetime": "YYYY-MM-DD HH:MM:SS"}."""
    body = await request.json()
    dt_str = body.get("datetime")
    if not dt_str:
        raise HTTPException(status_code=400, detail="Укажите datetime")

    try:
        if len(dt_str) == 16:  # "YYYY-MM-DD HH:MM"
            dt_str = dt_str + ":00"
        new_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Формат даты: YYYY-MM-DD HH:MM или YYYY-MM-DD HH:MM:SS",
        )

    record = get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    ok = update_record_datetime(record_id, new_dt)
    if not ok:
        raise HTTPException(status_code=500, detail="Не удалось обновить запись")

    logger.info(f"Запись {record_id} обновлена на {new_dt}")
    return {"status": "ok", "datetime": new_dt.isoformat(sep=" ")}


@router.get("/wheel/check/{user_id}")
async def check_spin(user_id: int):
    has_spin = has_user_spin(user_id)
    return {"has_spin": has_spin}


@router.post("/wheel/{user_id}")
async def spin_wheel(user_id: int, payload: dict):
    if has_user_spin(user_id):
        raise HTTPException(status_code=400, detail="Вы уже крутили колесо")

    prize_type = payload.get("prize_type")
    promo_code = payload.get("promo_code")

    if not prize_type:
        raise HTTPException(status_code=400, detail="Missing prize_type")

    save_spin(user_id, prize_type, promo_code)

    logger.info(
        f"Пользователь {user_id} выиграл приз {prize_type}, промокод: {promo_code}"
    )
    return {"status": "ok", "prize_type": prize_type, "promo_code": promo_code}
