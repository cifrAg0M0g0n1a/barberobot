from datetime import date, datetime
import sqlite3
from typing import List, Optional, Tuple
from pathlib import Path

from settings import DISCOUNT30, FREEFRIEND, LOSE

DB_PATH = str(Path(__file__).parent.parent / "database" / "db.sqlite3")


# ---------- Работа с пользователями ----------
def get_user_records(user_id: int) -> List[Tuple[int, str, str, str, str, int]]:
    """
    Возвращает все записи пользователя:
    (record_id, datetime, user_name, service_name, address, price)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            r.id,
            r.datetime,
            r.name,
            s.name,
            r.address,
            s.price
        FROM records r
        JOIN services s ON s.id = r.service_id
        WHERE r.user_id = ?
        ORDER BY r.datetime
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_records() -> List[Tuple[int, str, str, str, str, str, str, int]]:
    """
    Возвращает все записи:
    (record_id, datetime, name, service_name, address, phone, username, price)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            r.id,
            r.datetime,
            r.name,
            s.name,
            r.address,
            r.phone,
            u.username,
            s.price
        FROM records r
        JOIN users u ON u.id = r.user_id
        JOIN services s ON s.id = r.service_id
        ORDER BY r.datetime
        """,
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_record(record_id: int) -> None:
    """Удаляет запись по id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def update_record_datetime(record_id: int, new_datetime: datetime) -> bool:
    """Обновляет дату и время записи. Возвращает True при успехе."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE records SET datetime = ? WHERE id = ?",
        (new_datetime.isoformat(sep=" "), record_id),
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_past_records(hours: int = 2) -> List[Tuple[int, int, str]]:
    """
    Возвращает записи, которые прошли более указанного количества часов назад.
    Возвращает: (record_id, user_id, name)
    """
    from datetime import datetime, timedelta
    from settings import TIMEZONE

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT r.id, r.user_id, r.name, r.datetime
        FROM records r
        """
    )
    rows = cursor.fetchall()
    conn.close()

    now = datetime.now(TIMEZONE)
    threshold = now - timedelta(hours=hours)

    past_records = []
    for record_id, user_id, name, dt_str in rows:
        try:
            record_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

            if record_dt.tzinfo is None:
                record_dt = record_dt.replace(tzinfo=TIMEZONE)

            if record_dt < threshold:
                past_records.append((record_id, user_id, name))
        except Exception as e:
            continue

    return past_records


def add_user_if_not_exists(user_id: int, name: str, username: str) -> None:
    """Добавляет пользователя в таблицу users, если его нет"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (id, name, username) VALUES (?, ?, ?)",
            (user_id, name, username),
        )
        conn.commit()
    conn.close()


def get_record(record_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.user_id, r.name, r.datetime, u.username, s.name, r.address
        FROM records r
        JOIN users u ON u.id = r.user_id
        JOIN services s ON s.id = r.service_id
        WHERE r.id = ?
        """,
        (record_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def get_service(name: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price FROM services WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        service_id, name, price = row
        return {"id": service_id, "name": name, "price": price}
    return None


def get_service_by_id(service_id: int) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price FROM services WHERE id = ?", (service_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        sid, name, price = row
        return {"id": sid, "name": name, "price": price}
    return None


def get_all_services() -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price FROM services ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "price": r[2]} for r in rows]


def get_slots_for_date(selected_date: date) -> List[str]:
    """Возвращает занятые слоты на дату (общие для всех услуг — одно время = одна запись)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT datetime FROM records WHERE date(datetime) = ?",
        (selected_date.isoformat(),),
    )
    rows = cursor.fetchall()
    conn.close()
    slots = [
        datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").strftime("%H:%M") for row in rows
    ]
    return slots


def add_record_cut(
    user_id: int,
    datetime_obj: datetime,
    service_id: int,
    name: str,
    phone: str,
    address: str,
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO records (user_id, datetime, service_id, name, phone, address, created_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (user_id, datetime_obj.isoformat(sep=" "), service_id, name, phone, address),
    )

    record_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return record_id


def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, username FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def get_user_records_for_reminder():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT r.id, r.user_id, r.datetime, r.name, s.name AS service_name, s.price, r.address
        FROM records r
        JOIN services s ON r.service_id = s.id
        WHERE r.reminder_sent = 0
        """
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def mark_reminder_sent(record_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("UPDATE records SET reminder_sent = 1 WHERE id = ?", (record_id,))

    conn.commit()
    conn.close()


def has_user_spin(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM wheel_spins WHERE user_id = ? LIMIT 1",
        (user_id,),
    )
    result = cursor.fetchone()

    conn.close()
    return bool(result)


def save_spin(
    user_id: int,
    prize_type: str,
    promo_code: Optional[str],
) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO wheel_spins (user_id, prize_type, created_at)
        VALUES (?, ?, datetime('now'))
        """,
        (user_id, prize_type),
    )

    if promo_code:
        allow_owner = 1 if prize_type != FREEFRIEND else 0
        discount_percent = 30 if prize_type == DISCOUNT30 else None

        cursor.execute(
            """
            INSERT INTO promo_codes
                (code, prize_type, discount_percent, owner_user_id, allow_owner, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (promo_code, prize_type, discount_percent, user_id, allow_owner),
        )

    conn.commit()
    conn.close()


def get_promo_code(code: str) -> Optional[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, code, prize_type, discount_percent, owner_user_id, allow_owner, used, used_by, used_at
        FROM promo_codes
        WHERE code = ?
        """,
        (code,),
    )
    result = cursor.fetchone()

    conn.close()
    return result


def use_promo_code(code: str, user_id: int) -> bool:
    """
    Использует промокод для пользователя.
    Возвращает True, если промокод успешно использован, False в противном случае.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    promo = get_promo_code(code)
    if not promo:
        conn.close()
        return False

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
    ) = promo

    if used:
        conn.close()
        return False

    if user_id == owner_user_id and allow_owner == 0:
        conn.close()
        return False

    cursor.execute(
        """
        UPDATE promo_codes
        SET used = 1, used_by = ?, used_at = datetime('now')
        WHERE id = ?
        """,
        (user_id, promo_id),
    )

    conn.commit()
    conn.close()
    return True


# ---------- Прочие функции, при необходимости ----------
def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        username TEXT NOT NULL
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        price INTEGER NOT NULL
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        datetime TEXT NOT NULL,
        service_id INTEGER NOT NULL,
        phone TEXT NOT NULL,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        reminder_sent INTEGER NOT NULL DEFAULT(0),
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (service_id) REFERENCES services(id)
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS promo_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,

        prize_type TEXT NOT NULL, 

        discount_percent INTEGER,

        owner_user_id INTEGER NOT NULL,
        allow_owner INTEGER NOT NULL,

        used INTEGER NOT NULL DEFAULT 0,
        used_by INTEGER,
        used_at TEXT,

        created_at TEXT NOT NULL
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS wheel_spins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prize_type TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """
    )

    conn.commit()
    conn.close()


def seed_services():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executemany(
        """
    INSERT OR IGNORE INTO services (name, price)
    VALUES (?, ?)
    """,
        [
            ("Стрижка", 1500),
            ("Стрижка с бородой", 2000),
        ],
    )

    conn.commit()
    conn.close()
