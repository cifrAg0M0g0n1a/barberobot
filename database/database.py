import sqlite3
from typing import List, Tuple

DB_PATH = "database/db.sqlite3"


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
            s.name
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
        SELECT r.user_id, r.name, r.datetime, u.username, s.name
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


# ---------- Прочие функции, при необходимости ----------
def create_tables():
    """Создает все таблицы, если их нет"""
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
        name TEXT NOT NULL,
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
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (service_id) REFERENCES services(id)
    )
    """
    )

    conn.commit()
    conn.close()
