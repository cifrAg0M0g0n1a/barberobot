#!/bin/bash
# Скрипт для обновления проекта на сервере

set -e

PROJECT_DIR="/opt/barberobot"
SERVICE_USER="www-data"

echo "=== Обновление Barberobot ==="

if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

cd "$PROJECT_DIR"

source venv/bin/activate

echo "Обновление зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

chown -R $SERVICE_USER:$SERVICE_USER "$PROJECT_DIR"

echo "Перезапуск сервисов..."
systemctl restart barberobot-backend
sleep 3
systemctl restart barberobot-bot

echo ""
echo "=== Обновление завершено ==="
echo ""
echo "Проверка статуса:"
systemctl status barberobot-backend --no-pager -l
echo ""
systemctl status barberobot-bot --no-pager -l
