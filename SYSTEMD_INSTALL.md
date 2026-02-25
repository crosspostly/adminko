# Установка Telegram-бота как systemd сервиса

## Быстрая установка

1. **Создайте файл `.env` с токеном бота:**
   ```bash
   cp .env.example .env
   nano .env  # Вставьте ваш токен от @BotFather
   ```

2. **Запустите скрипт установки:**
   ```bash
   ./install_service.sh
   ```

3. **Проверьте статус:**
   ```bash
   sudo systemctl status adminko_bot
   ```

## Ручная установка

1. **Отредактируйте файл сервиса** (если нужно):
   ```bash
   nano adminko_bot.service
   ```
   Проверьте пути к директории и пользователю.

2. **Скопируйте файл сервиса:**
   ```bash
   sudo cp adminko_bot.service /etc/systemd/system/
   ```

3. **Перезагрузите systemd и включите сервис:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable adminko_bot
   sudo systemctl start adminko_bot
   ```

## Управление сервисом

| Команда | Описание |
|---------|----------|
| `sudo systemctl status adminko_bot` | Проверка статуса |
| `sudo systemctl stop adminko_bot` | Остановка |
| `sudo systemctl restart adminko_bot` | Перезапуск |
| `sudo systemctl disable adminko_bot` | Отключение автозапуска |

## Просмотр логов

```bash
# Логи в реальном времени
sudo journalctl -u adminko_bot -f

# Логи за последние 100 строк
sudo journalctl -u adminko_bot -n 100

# Логи за сегодня
sudo journalctl -u adminko_bot --since today
```

## Проверка телефона в боте

Телефон **`+7 (3842) 76-71-71`** указан в файле `texts.py`:
- Строка 109: Контакты
- Строка 120: Кнопка "Позвонить нам сейчас"

Для проверки:
```bash
grep "76-71-71" texts.py
```

## Безопасность

Сервис настроен с базовой защитой:
- `NoNewPrivileges=true` — запрет на повышение привилегий
- `PrivateTmp=true` — изолированный /tmp
- Запуск от имени пользователя `varsmana`

## Обновление бота

После изменений в коде:
```bash
sudo systemctl restart adminko_bot
```
