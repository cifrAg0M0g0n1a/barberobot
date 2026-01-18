from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from database.database import get_slots_for_date, get_service, add_record_cut
from settings import WORK_START, WORK_END, TIMEZONE, SERVICE_DURATION_MIN
from datetime import datetime, timedelta
from config import ADDRESS
from pathlib import Path

router = APIRouter()

timezone = TIMEZONE

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/address")
async def get_address():
    return ADDRESS


@router.get("/service")
async def get_service_info():
    """
    Возвращает данные об услуге по имени
    """
    service = get_service("Стрижка")
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"name": service["name"], "price": service["price"]}


@router.get("/slots")
async def get_slots(date: str):
    """
    Возвращает слоты для выбранной даты.
    Формат date: 'YYYY-MM-DD'
    """
    try:
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

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

    return slots


@router.post("/records")
async def book(request: Request):
    payload = await request.json()
    name = payload.get("name")
    phone = payload.get("phone")
    date_str = payload.get("date")
    time_str = payload.get("time")
    userId = payload.get("userId")

    if not all([name, phone, date_str, time_str, userId]):
        raise HTTPException(status_code=400, detail="Missing fields")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        time_obj = datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date or time format")

    service = get_service("Стрижка")
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    add_record_cut(
        user_id=userId,
        datetime_obj=datetime.combine(date_obj, time_obj),
        service_id=service["id"],
        name=name,
        phone=phone,
    )

    return {"message": "Запись успешно добавлена!"}
