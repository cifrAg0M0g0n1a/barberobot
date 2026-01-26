#!/bin/bash
# Скрипт для деплоя проекта на VPS

set -e

PROJECT_DIR="/opt/barberobot"
SERVICE_USER="www-data"
VENV_DIR="$PROJECT_DIR/venv"

echo "=== Деплой Barberobot ==="

if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

echo "Создание директории проекта..."
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/logs"

# Копирование файлов проекта (предполагается, что файлы уже скопированы)
# Если нужно, раскомментируйте:
# echo "Копирование файлов..."
# cp -r /path/to/source/* "$PROJECT_DIR/"

# Создание виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv "$VENV_DIR"
fi

echo "Установка зависимостей..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

echo "Установка прав доступа..."
chown -R $SERVICE_USER:$SERVICE_USER "$PROJECT_DIR"
chmod +x "$PROJECT_DIR/deploy/check_backend.sh"

echo "Установка systemd сервисов..."
cp "$PROJECT_DIR/deploy/barberobot-backend.service" /etc/systemd/system/
cp "$PROJECT_DIR/deploy/barberobot-bot.service" /etc/systemd/system/

systemctl daemon-reload

systemctl enable barberobot-backend.service
systemctl enable barberobot-bot.service

echo ""
echo "=== Деплой завершен ==="
echo ""
echo "Следующие шаги:"
echo "1. Убедитесь, что файл .env настроен в $PROJECT_DIR"
echo "2. Запустите сервисы:"
echo "   sudo systemctl start barberobot-backend"
echo "   sudo systemctl start barberobot-bot"
echo ""
echo "Проверка статуса:"
echo "   sudo systemctl status barberobot-backend"
echo "   sudo systemctl status barberobot-bot"
echo ""
echo "Просмотр логов:"
echo "   sudo journalctl -u barberobot-backend -f"
echo "   sudo journalctl -u barberobot-bot -f"
