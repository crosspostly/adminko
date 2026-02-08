#!/bin/bash

# Убедитесь, что TELEGRAM_BOT_TOKEN установлен в вашем окружении
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "Ошибка: Переменная окружения TELEGRAM_BOT_TOKEN не установлена."
  exit 1
fi

# Переходим в директорию, где находится bot.py
cd "$(dirname "$0")" || exit

# Запускаем бота
./venv/bin/python bot.py
