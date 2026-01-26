#!/bin/bash
# Скрипт для проверки готовности backend перед запуском bot

if [ -f /opt/barberobot/.env ]; then
    export $(grep -v '^#' /opt/barberobot/.env | xargs)
fi

BACKEND_URL="${WEBAPP_URL:-http://localhost:8000}"
MAX_ATTEMPTS=30
ATTEMPT=0

echo "Ожидание запуска backend на $BACKEND_URL..."

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Проверяем доступность backend через /service endpoint
    if curl -f -s --connect-timeout 2 "$BACKEND_URL/service" > /dev/null 2>&1; then
        echo "Backend готов!"
        exit 0
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    if [ $((ATTEMPT % 5)) -eq 0 ]; then
        echo "Попытка $ATTEMPT/$MAX_ATTEMPTS..."
    fi
    sleep 2
done

echo "Ошибка: Backend не запустился за отведенное время (60 секунд)"
echo "Проверьте логи: sudo journalctl -u barberobot-backend -n 50"
exit 1
