#!/bin/bash

# Устанавливаем токен
export TELEGRAM_BOT_TOKEN="8307388847:AAEJ54wuRqeCY5ehD7bPPg7T5nrpimCKQ6U"

# Переходим в директорию, где находится bot.py
cd "$(dirname "$0")" || exit

# Запускаем бота
./venv/bin/python bot.py
