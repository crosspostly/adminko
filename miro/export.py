import requests
import json
import time
import sys
import os

# Добавляем корень проекта в путь
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID

BASE_URL = f'https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/shapes'
CONNECTOR_URL = f'https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/connectors'

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
    'default': {'color': '#ffffff', 'border': '#000000', 'shape': 'rectangle'}
}

# ПОЛНЫЕ ТЕКСТЫ ИЗ ТВОЕГО БОТА
NODES = {
    'Start_Msg': ('<b>💬 Приветствие</b><br>Привет! 👋 Добро пожаловать в мир заботы о вашем ПК! Я — ваш надежный помощник...', 'msg', 0, -200),
    'Btn_StartTest': ('🔘 🚀 Начать Экспресс-тест', 'btn', -400, 0),
    'Btn_Services': ('🔘 💼 Наши услуги', 'btn', 0, 0),
    'Btn_Cabinet': ('🔘 👤 Личный кабинет', 'btn', 400, 0),
    'Btn_Contacts': ('🔘 ℹ️ Контакты', 'btn', 800, 0),
    'TQ1': ('<b>Вопрос 1/8:</b><br>Компьютер стал работать медленнее...?', 'msg', -800, 200),
    'TQ1_Ans': ('🔘 Да / Нет / Не знаю', 'btn', -800, 320),
    'TH1': ('<b>🔔 Hint (Popup)</b><br>Вероятно: Проблемы с диском. HDD -> SSD.', 'alert', -1100, 320),
    'TQ2': ('<b>Вопрос 2/8:</b><br>Вентиляторы шумят...?', 'msg', -800, 500),
    'TQ2_Ans': ('🔘 Да / Нет / Не знаю', 'btn', -800, 620),
    'TH2': ('<b>🔔 Hint (Popup)</b><br>Вероятно: Перегрев. Чистка.', 'alert', -1100, 620),
    'TQ3': ('<b>Вопрос 3/8:</b><br>Щелчки/Треск...?', 'msg', -800, 800),
    'TQ3_Ans': ('🔘 Да / Нет / Не знаю', 'btn', -800, 920),
    'TH3': ('<b>🔔 Hint (Popup)</b><br>Износ HDD. Срочно копия!', 'alert', -1100, 920),
    'TQ4': ('<b>Вопрос 4/8:</b><br>Полосы на экране...?', 'msg', -800, 1100),
    'TQ4_Ans': ('🔘 Да / Нет / Не знаю', 'btn', -800, 1220),
    'TH4': ('<b>🔔 Hint (Popup)</b><br>Видеокарта.', 'alert', -1100, 1220),
    'TQ5': ('<b>Вопрос 5/8:</b><br>Выключается сам...?', 'msg', -800, 1400),
    'TQ5_Ans': ('🔘 Да / Нет / Не знаю', 'btn', -800, 1520),
    'TH5': ('<b>🔔 Hint (Popup)</b><br>Блок питания.', 'alert', -1100, 1520),
    'TQ6': ('<b>Вопрос 6/8:</b><br>Писк...?', 'msg', -800, 1700),
    'TQ6_Ans': ('🔘 Да / Нет / Не знаю', 'btn', -800, 1820),
    'TH6': ('<b>🔔 Hint (Popup)</b><br>Ошибка оборудования.', 'alert', -1100, 1820),
    'TQ7': ('<b>Вопрос 7/8:</b><br>Windows 7...?', 'msg', -800, 2000),
    'TQ7_Ans': ('🔘 Да / Нет / Не знаю', 'btn', -800, 2120),
    'TH7': ('<b>🔔 Hint (Popup)</b><br>Устаревшая ОС.', 'alert', -1100, 2120),
    'TQ8': ('<b>Вопрос 8/8:</b><br>Вирусы...?', 'msg', -800, 2300),
    'TQ8_Ans': ('🔘 Да / Нет / Не знаю', 'btn', -800, 2420),
    'TH8': ('<b>🔔 Hint (Popup)</b><br>Вирусы. Нужна очистка.', 'alert', -1100, 2420),
    'Test_Results': ('<b>📊 Результаты</b><br>🎁 Начислено 1000 бонусов!', 'msg', -800, 2700),
    'Btn_Order_Diag_Test': ('🔘 Заказать диагностику 🛠️', 'btn', -800, 2850),
    'Srv_Msg': ('<b>💼 Наши услуги:</b>', 'msg', 0, 400),
    'Btn_S_Repair': ('🔘 Ремонт ПК 💻', 'btn', -250, 550),
    'Btn_S_IT': ('🔘 IT-администрирование 🏢', 'btn', 0, 550),
    'Btn_S_Video': ('🔘 Видеонаблюдение 📹', 'btn', 250, 550),
    'S_Repair_Detail': ('<b>💻 Ремонт ПК:</b><br>Любая сложность. Гарантия.', 'msg', -250, 750),
    'S_IT_Detail': ('<b>🏢 IT-поддержка:</b><br>Обслуживание организаций.', 'msg', 0, 750),
    'S_Video_Detail': ('<b>📹 Видеонаблюдение:</b><br>Монтаж СКС, СКУД.', 'msg', 250, 750),
    'Btn_D1': ('🔘 Заказать диагностику 🛠️', 'btn', -250, 900),
    'Btn_D2': ('🔘 Заказать диагностику 🛠️', 'btn', 0, 900),
    'Btn_D3': ('🔘 Заказать диагностику 🛠️', 'btn', 250, 900),
    'Cab_Msg_Full': ('<b>👤 Личный кабинет</b><br>Баланс: {points}', 'msg', 400, 400),
    'Btn_Use_Points': ('🔘 Использовать баллы', 'btn', 400, 550),
    'Code_Generated': ('<b>🔑 Код: {code}</b>', 'msg', 400, 700),
    'Diag_Menu': ('<b>🛠️ Диагностика</b><br>Свяжитесь с нами:', 'msg', 0, 1100),
    'Btn_Request_Callback': ('🔘 Заказать звонок 📞', 'btn', 0, 1250),
    'Ask_Phone': ('<b>📱 Номер телефона?</b><br>Поделитесь кнопкой или введите.', 'msg', 0, 1400),
    'Btn_Share_Contact': ('📱 Поделиться номером (Reply)', 'btn', -200, 1550),
    'Phone_Input_Manual': ('⌨️ Ввод вручную', 'btn', 200, 1550),
    'Phone_Success': ('<b>✅ Успех!</b><br>Свяжемся с вами.', 'msg', 0, 1750),
    'Contacts_Msg': ('<b>📞 Контакты</b><br>admin-ko.ru', 'msg', 800, 400),
    'Admin_Start': ('<b>👨‍💼 МЕНЕДЖЕР</b><br>/admin_redeem_points', 'msg', 1300, 0),
    'A_Ask_Code': ('📄 Введите код клиента', 'msg', 1300, 200),
    'A_Ask_Sum': ('📄 Введите сумму', 'msg', 1300, 400),
    'A_Preview': ('<b>📊 Расчет</b><br>Итого к оплате...', 'msg', 1300, 600),
    'Btn_A_Send': ('🔘 Отправить клиенту', 'btn', 1150, 750),
    'Btn_A_Cancel': ('🔘 Отмена', 'btn', 1450, 750),
    'Client_Confirm_Screen': ('<b>📱 КЛИЕНТУ:</b> Подтвердите?', 'msg', 1300, 950),
    'Btn_C_Confirm': ('🔘 Подтвердить', 'btn', 1150, 1100),
    'Btn_C_Cancel': ('🔘 Отклонить', 'btn', 1450, 1100),
    'Redeem_Done': ('<b>✅ Успех!</b>', 'msg', 1300, 1250)
}

EDGES = [
    ('Start_Msg', 'Btn_StartTest', ''), ('Start_Msg', 'Btn_Services', ''), ('Start_Msg', 'Btn_Cabinet', ''), ('Start_Msg', 'Btn_Contacts', ''),
    ('Btn_StartTest', 'TQ1', ''), ('TQ1', 'TQ1_Ans', ''), ('TQ1_Ans', 'TH1', ''), ('TH1', 'TQ2', ''),
    ('TQ2', 'TQ2_Ans', ''), ('TQ2_Ans', 'TH2', ''), ('TH2', 'TQ3', ''),
    ('TQ3', 'TQ3_Ans', ''), ('TQ3_Ans', 'TH3', ''), ('TH3', 'TQ4', ''),
    ('TQ4', 'TQ4_Ans', ''), ('TQ4_Ans', 'TH4', ''), ('TH4', 'TQ5', ''),
    ('TQ5', 'TQ5_Ans', ''), ('TQ5_Ans', 'TH5', ''), ('TH5', 'TQ6', ''),
    ('TQ6', 'TQ6_Ans', ''), ('TQ6_Ans', 'TH6', ''), ('TH6', 'TQ7', ''),
    ('TQ7', 'TQ7_Ans', ''), ('TQ7_Ans', 'TH7', ''), ('TH7', 'TQ8', ''),
    ('TQ8', 'TQ8_Ans', ''), ('TQ8_Ans', 'TH8', ''), ('TH8', 'Test_Results', ''),
    ('Test_Results', 'Btn_Order_Diag_Test', ''), ('Btn_Order_Diag_Test', 'Diag_Menu', ''),
    ('Btn_Services', 'Srv_Msg', ''), ('Srv_Msg', 'Btn_S_Repair', ''), ('Srv_Msg', 'Btn_S_IT', ''), ('Srv_Msg', 'Btn_S_Video', ''),
    ('Btn_S_Repair', 'S_Repair_Detail', ''), ('Btn_S_IT', 'S_IT_Detail', ''), ('Btn_S_Video', 'S_Video_Detail', ''),
    ('S_Repair_Detail', 'Btn_D1', ''), ('S_IT_Detail', 'Btn_D2', ''), ('S_Video_Detail', 'Btn_D3', ''),
    ('Btn_D1', 'Diag_Menu', ''), ('Btn_D2', 'Diag_Menu', ''), ('Btn_D3', 'Diag_Menu', ''),
    ('Cab_Msg_Full', 'Btn_Use_Points', ''), ('Btn_Use_Points', 'Code_Generated', ''),
    ('Diag_Menu', 'Btn_Request_Callback', ''), ('Btn_Request_Callback', 'Ask_Phone', ''),
    ('Ask_Phone', 'Btn_Share_Contact', ''), ('Ask_Phone', 'Phone_Input_Manual', ''),
    ('Btn_Share_Contact', 'Phone_Success', ''), ('Phone_Input_Manual', 'Phone_Success', ''),
    ('Btn_Contacts', 'Contacts_Msg', ''),
    ('Admin_Start', 'A_Ask_Code', ''), ('A_Ask_Code', 'A_Ask_Sum', ''), ('A_Ask_Sum', 'A_Preview', ''),
    ('A_Preview', 'Btn_A_Send', ''), ('A_Preview', 'Btn_A_Cancel', ''),
    ('Btn_A_Send', 'Client_Confirm_Screen', ''), ('Client_Confirm_Screen', 'Btn_C_Confirm', ''), ('Client_Confirm_Screen', 'Btn_C_Cancel', ''),
    ('Btn_C_Confirm', 'Redeem_Done', '')
]

class MiroExporter:
    def __init__(self):
        self.node_map = {}

    def create_shape(self, text, style_key, x, y):
        style = STYLES.get(style_key, STYLES['default'])
        data = {
            "data": {"content": text, "shape": style['shape']},
            "style": {"fillColor": style['color'], "borderColor": style['border'], "borderWidth": "2.0", "textAlign": "center"},
            "position": {"x": x, "y": y},
            "geometry": {"width": 280, "height": 110}
        }
        res = requests.post(BASE_URL, headers=HEADERS, json=data)
        if res.status_code == 201: return res.json()['id']
        return None

    def create_connector(self, start_id, end_id, label=""):
        data = {"startItem": {"id": start_id}, "endItem": {"id": end_id}, "captions": [{"content": label}] if label else []}
        requests.post(CONNECTOR_URL, headers=HEADERS, json=data)

    def run(self):
        print(f"Exporting {len(NODES)} nodes...")
        mapping = {}
        for node_id, (label, style, x, y) in NODES.items():
            miro_id = self.create_shape(label, style, x, y)
            if miro_id:
                self.node_map[node_id] = miro_id
                mapping[miro_id] = node_id
            time.sleep(0.4)
        
        with open('memory/miro_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
        print("Mapping saved.")

        for start, end, label in EDGES:
            if start in self.node_map and end in self.node_map:
                self.create_connector(self.node_map[start], self.node_map[end], label)
                time.sleep(0.4)
        print("Done!")

if __name__ == "__main__":
    MiroExporter().run()
