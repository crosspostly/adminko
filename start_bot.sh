#!/bin/bash

# Устанавливаем токен
export TELEGRAM_BOT_TOKEN="8307388847:AAGHjrtWjv9B-p8zLkjkgPLLfjz6jK7Hb6A"

# Переходим в директорию, где находится bot.py
cd "$(dirname "$0")" || exit

# Запускаем бота
./venv/bin/python bot.py
