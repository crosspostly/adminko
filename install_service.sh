#!/bin/bash
# Скрипт установки Telegram-бота как systemd сервиса

set -e

CURRENT_USER=$(whoami)
BOT_DIR="/home/$CURRENT_USER/adminko"
SERVICE_NAME="adminko_bot"
SERVICE_FILE="$BOT_DIR/$SERVICE_NAME.service"

echo "🔧 Установка systemd сервиса для бота..."
echo "   Пользователь: $CURRENT_USER"
echo "   Директория: $BOT_DIR"
echo ""

# Проверка, что файл сервиса существует
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Файл сервиса не найден: $SERVICE_FILE"
    exit 1
fi

# Проверка виртуального окружения
if [ ! -d "$BOT_DIR/venv" ]; then
    echo "❌ Виртуальное окружение не найдено: $BOT_DIR/venv"
    exit 1
fi

# Проверка .env файла
if [ ! -f "$BOT_DIR/.env" ]; then
    echo "⚠️  Файл .env не найден. Создайте его с TELEGRAM_BOT_TOKEN"
    echo "    Пример: TELEGRAM_BOT_TOKEN=\"123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11\""
    echo ""
    echo "📋 Можно скопировать из шаблона:"
    echo "    cp $BOT_DIR/.env.example $BOT_DIR/.env"
    exit 1
fi

# Обновляем путь к пользователю в сервисе
echo "📝 Обновляем пользователя в сервисе на: $CURRENT_USER"
sed -i "s/^User=.*/User=$CURRENT_USER/" "$SERVICE_FILE"
sed -i "s/^Group=.*/Group=$CURRENT_USER/" "$SERVICE_FILE"
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$BOT_DIR|" "$SERVICE_FILE"
sed -i "s|EnvironmentFile=.*|EnvironmentFile=$BOT_DIR/.env|" "$SERVICE_FILE"
sed -i "s|ExecStart=.*|ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/bot.py|" "$SERVICE_FILE"

# Копируем файл сервиса в systemd
echo "📋 Копирование файла сервиса в /etc/systemd/system/..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Перезагружаем systemd
echo "🔄 Перезагрузка systemd..."
sudo systemctl daemon-reload

# Включаем автозапуск
echo "▶️  Включение автозапуска..."
sudo systemctl enable $SERVICE_NAME

# Запускаем бота
echo "🚀 Запуск бота..."
sudo systemctl start $SERVICE_NAME

# Пауза для запуска
sleep 2

# Проверка статуса
echo ""
echo "📊 Статус сервиса:"
sudo systemctl status $SERVICE_NAME --no-pager -l

echo ""
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Бот успешно запущен!"
else
    echo "❌ Бот не запустился. Проверьте логи:"
    echo "   sudo journalctl -u $SERVICE_NAME -n 50"
fi

echo ""
echo "Полезные команды:"
echo "  sudo systemctl status $SERVICE_NAME     # Проверка статуса"
echo "  sudo systemctl stop $SERVICE_NAME       # Остановка"
echo "  sudo systemctl restart $SERVICE_NAME    # Перезапуск"
echo "  sudo journalctl -u $SERVICE_NAME -f     # Просмотр логов"
