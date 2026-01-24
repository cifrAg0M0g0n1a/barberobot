from datetime import date, datetime
import sqlite3
from typing import List, Optional, Tuple
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent / "database" / "db.sqlite3")


# ---------- Работа с пользователями ----------
def get_user_records(user_id: int) -> List[Tuple[int, str, str, str]]:
    """
    Возвращает все записи пользователя:
    (record_id, datetime, user_name, service_name)
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
            r.address
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


def delete_record(record_id: int) -> None:
    """Удаляет запись по id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


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


def get_slots_for_date(selected_date: date) -> List[str]:
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
    conn.commit()
    conn.close()


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
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (service_id) REFERENCES services(id)
    )
    """
    )

    conn.commit()
    conn.close()


def seed_services():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
    INSERT OR IGNORE INTO services (name, price)
    VALUES (?, ?)
    """,
        ("Стрижка", 1500),
    )

    conn.commit()
    conn.close()
