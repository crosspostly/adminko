import requests
import time
import sys
import os

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID

BASE_URL = f'https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/shapes'
HEADERS = {
    'Authorization': f'Bearer {MIRO_ACCESS_TOKEN}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

STYLES = {
    'msg': {'color': '#f9f1ff', 'border': '#7a00e6', 'shape': 'rectangle'},
    'btn': {'color': '#e1f5fe', 'border': '#0288d1', 'shape': 'round_rectangle'},
    'logic': {'color': '#fff9c4', 'border': '#fbc02d', 'shape': 'rhombus'},
    'alert': {'color': '#ffe0b2', 'border': '#f57c00', 'shape': 'rectangle'},
    'header': {'color': '#e1f5fe', 'border': '#0288d1', 'shape': 'rectangle'},
}

# Координаты X для FAQ вынесем левее основной схемы
FAQ_X = -2500

FAQ_NODES = [
    # Заголовок
    ('💎 <b>ИНСТРУКЦИЯ ПО УПРАВЛЕНИЮ БОТОМ</b>', 'header', FAQ_X, -800, 700, 120),
    
    # Стили блоков
    ('''🎨 <b>ЦВЕТА И ТИПЫ БЛОКОВ</b><br><br>
🟪 <b>Фиолетовый (msg):</b> Текст сообщения в Telegram.<br>
<i>Поддерживает HTML: &lt;b&gt;, &lt;i&gt;, &lt;code&gt;.</i><br><br>
🟦 <b>Голубой (btn):</b> Узел-заглушка для кнопок.<br>
<i>Сами кнопки создаются из <u>надписей на стрелках</u>.</i><br><br>
🟧 <b>Оранжевый (alert):</b> Всплывающая подсказка (Toast).<br>
<i>Появляется при нажатии на кнопку, если блок соединен со стрелкой.</i><br><br>
🔷 <b>Ромб (logic):</b> Техническая логика (например, Тесты).''', 
     'msg', FAQ_X, -500, 500, 350),

    # Связи
    ('''🔗 <b>СТРЕЛКИ = КНОПКИ В МЕНЮ</b><br><br>
1. <b>Текст на стрелке:</b> Станет текстом кнопки в Telegram.<br><br>
2. <b>Куда ведет стрелка:</b> Тот блок бот пришлет следующим.<br><br>
3. <b>Пустая стрелка:</b> Авто-переход. Бот сразу пришлет следующее сообщение (используется для длинных текстов).''',
     'msg', FAQ_X, -50, 500, 250),

    # Технические теги
    ('''⚙️ <b>СВЯЗЬ С КОДОМ: ТЕГИ {#...}</b><br><br>
В начале текста ОБЯЗАТЕЛЬНО должен быть тег в фигурных скобках:<br><br>
• <code>{#Start_Msg}</code> — Главное меню.<br>
• <code>{#Srv_Msg}</code> — Меню услуг.<br><br>
🚀 <b>ВАЖНО:</b> Если вы меняете текст сообщения, <b>не удаляйте тег</b> в начале! По нему бот понимает, какую переменную из <code>texts.py</code> использовать.''',
     'msg', FAQ_X, 250, 500, 250),

    # Спец-кнопки
    ('''🚀 <b>СПЕЦИАЛЬНЫЕ ФУНКЦИИ</b><br><br>
Если текст на стрелке совпадает с этими кодами, сработает спец. логика:<br><br>
• <code>start_test</code> — Запуск теста на 8 вопросов.<br>
• <code>request_callback</code> — Запрос телефона у юзера.<br>
• <code>use_points_start</code> — Генерация промокода.<br>
• <code>start_menu_main</code> — Возврат в самое начало.''',
     'msg', FAQ_X, 550, 500, 250),

    # Обновление
    ('''🔄 <b>КАК СОХРАНИТЬ ИЗМЕНЕНИЯ</b><br><br>
1. Отредактируйте текст или переставьте стрелки на доске.<br><br>
2. Запустите скрипт: <code>python3 miro/manager.py</code>.<br><br>
3. Бот мгновенно обновит меню для всех пользователей без перезагрузки!''',
     'msg', FAQ_X, 850, 500, 220)
]

def create_shape(text, style_key, x, y, width=280, height=110):
    style = STYLES.get(style_key, STYLES['msg'])
    data = {
        "data": {"content": text, "shape": style['shape']},
        "style": {"fillColor": style['color'], "borderColor": style['border'], "borderWidth": "2.0", "textAlign": "left"},
        "position": {"x": x, "y": y},
        "geometry": {"width": width, "height": height}
    }
    res = requests.post(BASE_URL, headers=HEADERS, json=data)
    if res.status_code == 201:
        print(f"Created FAQ block at y={y}")
        return res.json()['id']
    else:
        print(f"Error: {res.status_code} - {res.text}")
    return None

if __name__ == "__main__":
    print(f"Recreating FAQ on Miro board {MIRO_BOARD_ID}...")
    for text, style, x, y, w, h in FAQ_NODES:
        create_shape(text, style, x, y, w, h)
        time.sleep(0.5)
    print("Done! FAQ blocks are now more spacious.")
