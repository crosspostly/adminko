#!/bin/bash

# Путь к директории проекта
PROJECT_DIR="$(dirname "$0")"
cd "$PROJECT_DIR" || exit

# Загружаем переменные окружения
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "--- Starting Adminko Low-Code Platform ---"

# 1. Watcher (Документация)
./venv/bin/python tools/watcher.py > watcher.log 2>&1 &
WATCHER_PID=$!
echo "[+] Watcher started (PID: $WATCHER_PID)"

# 2. AutoSync (Miro -> Bot) - ОТКЛЮЧЕНО ПО ПРОСЬБЕ ПОЛЬЗОВАТЕЛЯ
# ./venv/bin/python miro/auto_sync.py > autosync.log 2>&1 &
# SYNC_PID=$!
# echo "[+] Miro AutoSync started (PID: $SYNC_PID)"

# 3. Основной бот
echo "[+] Starting Telegram Bot..."
./venv/bin/python bot.py

# Cleanup
echo "--- Shutting down ---"
kill $WATCHER_PID
# kill $SYNC_PID
echo "[!] Services stopped."
