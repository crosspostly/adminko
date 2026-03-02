import requests
import json
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID
import texts 

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
    'alert': {'color': '#ffe0b2', 'border': '#f57c00', 'shape': 'rectangle'},
    'logic': {'color': '#fff9c4', 'border': '#fbc02d', 'shape': 'rhombus'},
    'header': {'color': '#e1f5fe', 'border': '#0288d1', 'shape': 'rectangle'},
}

MAIN_X = 0
TEST_X = -1200
SRV_X = 0
CAB_X = 1200
ADM_X = 2400
RETENTION_X = -2400 # New column for retention funnel

# ПОЛНЫЙ СПИСОК УЗЛОВ С РЕАЛЬНЫМИ ТЕКСТАМИ
NODES = {
    # --- HEADER ---
    'H_Retention': ('⬅️ ВОРОНКА УДЕРЖАНИЯ', 'header', RETENTION_X, -600, 400, 50),
    'H_Main': ('⬇️ ГЛАВНОЕ МЕНЮ', 'header', MAIN_X, -600, 400, 50),
    'H_Test': ('➡️ ЭКСПРЕСС-ТЕСТ', 'header', TEST_X, -600, 400, 50),
    'H_Cabinet': ('➡️ ЛИЧНЫЙ КАБИНЕТ', 'header', CAB_X, -600, 400, 50),
    'H_Admin': ('➡️ АДМИН-ПАНЕЛЬ', 'header', ADM_X, -600, 400, 50),

    # --- ВОРОНКА УДЕРЖАНИЯ ---
    'Deeplink_Entry': ('Вход по ссылке\n`start=maps_1500`', 'logic', RETENTION_X, -400, 300, 100),
    'Deeplink_Bonus_Msg': (texts.DEEPLINK_BONUS_NOTIFICATION, 'msg', RETENTION_X, -200, 450, 200),
    'Btn_DL_Callback': ('Помощь специалиста 📞', 'btn', RETENTION_X - 150, 50, 250, 80),
    'Btn_DL_Cabinet': ('👤 Личный кабинет', 'btn', RETENTION_X + 150, 50, 250, 80),
    'Logic_2h_delay': ('Прошло 2 часа', 'logic', RETENTION_X, 300, 250, 80),
    'Timed_Test_Offer': (texts.TEST_OFFER_REMINDER, 'msg', RETENTION_X, 500, 400, 200),
    'Logic_1d_delay': ('Прошел 1 день', 'logic', RETENTION_X - 350, 750, 250, 80),
    'Retention_Callback': (texts.RETENTION_CALLBACK_REMINDER, 'msg', RETENTION_X - 350, 950, 400, 200),
    'Logic_10d_delay': ('Прошло 10 дней', 'logic', RETENTION_X + 350, 750, 250, 80),
    'Retention_Expiry': (texts.RETENTION_EXPIRY_REMINDER, 'msg', RETENTION_X + 350, 950, 400, 150),

    # --- ГЛАВНОЕ МЕНЮ ---
    'Start_Msg': (texts.START_NEW_USER, 'msg', MAIN_X, -400, 450, 200),
    'Btn_StartTest': ('🚀 Начать Экспресс-тест', 'btn', MAIN_X - 450, -150, 250, 80),
    'Btn_Services': ('💼 Наши услуги', 'btn', MAIN_X - 150, -150, 250, 80),
    'Btn_Cabinet': ('👤 Личный кабинет', 'btn', MAIN_X + 150, -150, 250, 80),
    'Btn_Contacts': ('ℹ️ Контакты', 'btn', MAIN_X + 450, -150, 250, 80),

    # --- ВЕТКА: ТЕСТ (8 ВОПРОСОВ) ---
    'TQ1': (texts.TQ1, 'msg', TEST_X, 0, 350, 150),
    'TQ1_Ans': ('Да / Нет / Не знаю', 'btn', TEST_X, 150, 250, 70),
    'TH1': (texts.TH1, 'alert', TEST_X - 400, 150, 300, 150),
    'TQ2': (texts.TQ2, 'msg', TEST_X, 350, 350, 150),
    'TQ2_Ans': ('Да / Нет / Не знаю', 'btn', TEST_X, 500, 250, 70),
    'TH2': (texts.TH2, 'alert', TEST_X - 400, 500, 300, 150),
    'TQ3': (texts.TQ3, 'msg', TEST_X, 700, 350, 150),
    'TQ3_Ans': ('Да / Нет / Не знаю', 'btn', TEST_X, 850, 250, 70),
    'TH3': (texts.TH3, 'alert', TEST_X - 400, 850, 300, 150),
    'TQ4': (texts.TQ4, 'msg', TEST_X, 1050, 350, 150),
    'TQ4_Ans': ('Да / Нет / Не знаю', 'btn', TEST_X, 1200, 250, 70),
    'TH4': (texts.TH4, 'alert', TEST_X - 400, 1200, 300, 150),
    'TQ5': (texts.TQ5, 'msg', TEST_X, 1400, 350, 150),
    'TQ5_Ans': ('Да / Нет / Не знаю', 'btn', TEST_X, 1550, 250, 70),
    'TH5': (texts.TH5, 'alert', TEST_X - 400, 1550, 300, 150),
    'TQ6': (texts.TQ6, 'msg', TEST_X, 1750, 350, 150),
    'TQ6_Ans': ('Да / Нет / Не знаю', 'btn', TEST_X, 1900, 250, 70),
    'TH6': (texts.TH6, 'alert', TEST_X - 400, 1900, 300, 150),
    'TQ7': (texts.TQ7, 'msg', TEST_X, 2100, 350, 150),
    'TQ7_Ans': ('Да / Нет / Не знаю', 'btn', TEST_X, 2250, 250, 70),
    'TH7': (texts.TH7, 'alert', TEST_X - 400, 2250, 300, 150),
    'TQ8': (texts.TQ8, 'msg', TEST_X, 2450, 350, 150),
    'TQ8_Ans': ('Да / Нет / Не знаю', 'btn', TEST_X, 2600, 250, 70),
    'TH8': (texts.TH8, 'alert', TEST_X - 400, 2600, 300, 150),
    'Test_Results': (texts.TEST_RESULTS_INTRO + texts.TEST_RESULTS_BONUS_NEW, 'msg', TEST_X, 2850, 450, 200),
    'Btn_Order_Diag_Test': ('Заказать бесплатную диагностику 🛠️', 'btn', TEST_X, 3050, 300, 80),

    # --- ВЕТКА: УСЛУГИ ---
    'Srv_Msg': (texts.OUR_SERVICES_TITLE, 'msg', SRV_X, 100, 400, 150),
    'Btn_S_Repair': ('Ремонт ПК/Ноутбуков 💻', 'btn', SRV_X - 350, 300, 280, 80),
    'Btn_S_IT': ('Системное администрирование 🏢', 'btn', SRV_X, 300, 280, 80),
    'Btn_S_Video': ('Видеонаблюдение, СКС, СКУД 📹', 'btn', SRV_X + 350, 300, 280, 80),
    'S_Repair_Detail': (texts.SERVICE_REPAIR_PC_NOTEBOOKS_TEXT, 'msg', SRV_X - 350, 500, 350, 150),
    'S_IT_Detail': (texts.SERVICE_IT_SUPPORT_TEXT, 'msg', SRV_X, 500, 350, 150),
    'S_Video_Detail': (texts.SERVICE_VIDEO_SURVEILLANCE_TEXT, 'msg', SRV_X + 350, 500, 350, 150),
    'Btn_D1': ('Заказать диагностику 🛠️', 'btn', SRV_X - 350, 700, 250, 70),
    'Btn_D2': ('Заказать диагностику 🛠️', 'btn', SRV_X, 700, 250, 70),
    'Btn_D3': ('Заказать диагностику 🛠️', 'btn', SRV_X + 350, 700, 250, 70),

    # --- СБОР ТЕЛЕФОНА (ДИАГНОСТИКА) ---
    'Diag_Menu': (texts.DIAGNOSTIC_REQUEST_TEXT, 'msg', SRV_X, 950, 450, 200),
    'Btn_Request_Callback': ('Заказать звонок 📞', 'btn', SRV_X, 1150, 250, 80),
    'Ask_Phone': (texts.REQUEST_PHONE_NUMBER_TEXT, 'msg', SRV_X, 1350, 400, 150),
    'Btn_Share_Contact': ('Поделиться номером', 'btn', SRV_X - 150, 1550, 250, 80),
    'Phone_Input_Manual': ('Ввести вручную', 'logic', SRV_X + 150, 1550, 250, 80),
    'Phone_Success': (texts.PHONE_RECEIVED_CONFIRMATION, 'msg', SRV_X, 1750, 400, 150),

    # --- ЛИЧНЫЙ КАБИНЕТ И ОТЗЫВЫ ---
    'Cab_Msg_Full': (texts.CABINET_HAS_POINTS_TITLE + texts.CABINET_USE_POINTS_PROMPT, 'msg', CAB_X, 100, 400, 150),
    'Btn_Use_Points': ('Использовать баллы', 'btn', CAB_X, 300, 250, 80),
    'Code_Generated': (texts.USE_POINTS_CODE_GENERATED, 'msg', CAB_X, 500, 400, 150),
    'Btn_Callback_After_Code': ('Заказать обратный звонок 📞', 'btn', CAB_X, 650, 280, 80),
    'Review_Request': (texts.RETENTION_REVIEW_REQUEST, 'msg', CAB_X, 900, 450, 200),
    'Btn_Get_Review_Bonus': ('Оставить отзыв и получить бонусы', 'btn', CAB_X, 1100, 300, 80),
    'Review_Bonus_Menu': (texts.REVIEW_BONUS_MENU_TITLE, 'msg', CAB_X, 1300, 450, 250),
    'Review_Proof': ('Отправка скриншота\nили текста', 'logic', CAB_X, 1550, 250, 80),
    'Review_Received': (texts.REVIEW_PROOF_RECEIVED, 'msg', CAB_X, 1750, 400, 150),

    # --- КОНТАКТЫ ---
    'Contacts_Msg': (texts.CONTACT_US_TITLE + texts.CONTACT_US_TEXT, 'msg', MAIN_X + 800, -150, 400, 250),

    # --- АДМИН ПАНЕЛЬ ---
    'Admin_Start': ('👨‍💼 <b>МЕНЕДЖЕР: ПАНЕЛЬ</b>', 'msg', ADM_X, 0, 350, 100),
    'A_Ask_Code': (texts.ADMIN_ENTER_CODE_PROMPT, 'msg', ADM_X, 200, 350, 100),
    'A_Ask_Sum': (texts.ADMIN_ENTER_ORDER_SUM, 'msg', ADM_X, 400, 350, 100),
    'A_Preview': (texts.ADMIN_PREVIEW_CALCULATION, 'msg', ADM_X, 650, 450, 250),
    'Btn_A_Send': ('Отправить подтверждение клиенту', 'btn', ADM_X - 200, 850, 300, 80),
    'Btn_A_Cancel': ('Отмена', 'btn', ADM_X + 200, 850, 250, 80),
    'Client_Confirm_Screen': (texts.CLIENT_CONFIRM_REQUEST, 'msg', ADM_X, 1100, 450, 200),
    'Btn_C_Confirm': ('Подтвердить списание', 'btn', ADM_X - 150, 1300, 250, 80),
    'Btn_C_Cancel': ('Отклонить', 'btn', ADM_X + 150, 1300, 250, 80),
    'Redeem_Done': (texts.CLIENT_REDEEM_SUCCESS, 'msg', ADM_X, 1500, 400, 150),
    'Admin_Verify_Review': (texts.ADMIN_NEW_REVIEW_PROOF, 'msg', ADM_X, 1750, 450, 250),
    'Btn_Verify_Approve': ('✅ Одобрить', 'btn', ADM_X - 150, 1950, 200, 80),
    'Btn_Verify_Reject': ('❌ Отклонить', 'btn', ADM_X + 150, 1950, 200, 80)
}

EDGES = [
    # Воронка
    ('Deeplink_Entry', 'Deeplink_Bonus_Msg', ''),
    ('Deeplink_Bonus_Msg', 'Btn_DL_Callback', 'Помощь специалиста 📞'),
    ('Deeplink_Bonus_Msg', 'Btn_DL_Cabinet', '👤 Личный кабинет'),
    ('Btn_DL_Callback', 'Diag_Menu', ''), # Ведет на ту же ветку
    ('Btn_DL_Cabinet', 'Cab_Msg_Full', ''),
    ('Deeplink_Bonus_Msg', 'Logic_2h_delay', 'Через 2 часа'),
    ('Logic_2h_delay', 'Timed_Test_Offer', ''),
    ('Deeplink_Bonus_Msg', 'Logic_1d_delay', 'Через 1 день'),
    ('Logic_1d_delay', 'Retention_Callback', ''),
    ('Deeplink_Bonus_Msg', 'Logic_10d_delay', 'Через 10 дней'),
    ('Logic_10d_delay', 'Retention_Expiry', ''),
    ('Timed_Test_Offer', 'Btn_StartTest', '🚀 Пройти Экспресс-тест'),

    # Меню -> Ветки
    ('Start_Msg', 'Btn_StartTest', '🚀 Начать Экспресс-тест'),
    ('Start_Msg', 'Btn_Services', '💼 Наши услуги'),
    ('Start_Msg', 'Btn_Cabinet', '👤 Личный кабинет'),
    ('Start_Msg', 'Btn_Contacts', 'ℹ️ Контакты'),

    # Тест
    ('Btn_StartTest', 'TQ1', ''),
    ('TQ1_Ans', 'TH1', 'Да / Нет / Не знаю'),
    ('TH1', 'TQ2', ''),
    ('TQ2_Ans', 'TH2', 'Да / Нет / Не знаю'),
    ('TH2', 'TQ3', ''),
    ('TQ3_Ans', 'TH3', 'Да / Нет / Не знаю'),
    ('TH3', 'TQ4', ''),
    ('TQ4_Ans', 'TH4', 'Да / Нет / Не знаю'),
    ('TH4', 'TQ5', ''),
    ('TQ5_Ans', 'TH5', 'Да / Нет / Не знаю'),
    ('TH5', 'TQ6', ''),
    ('TQ6_Ans', 'TH6', 'Да / Нет / Не знаю'),
    ('TH6', 'TQ7', ''),
    ('TQ7_Ans', 'TH7', 'Да / Нет / Не знаю'),
    ('TH7', 'TQ8', ''),
    ('TQ8_Ans', 'TH8', 'Да / Нет / Не знаю'),
    ('TH8', 'Test_Results', ''),
    ('Test_Results', 'Btn_Order_Diag_Test', 'Заказать диагностику 🛠️'),
    ('Btn_Order_Diag_Test', 'Diag_Menu', ''),

    # Услуги
    ('Btn_Services', 'Srv_Msg', ''),
    ('Srv_Msg', 'Btn_S_Repair', 'Ремонт ПК'),
    ('Srv_Msg', 'Btn_S_IT', 'IT-поддержка'),
    ('Srv_Msg', 'Btn_S_Video', 'Видеонаблюдение'),
    ('Btn_S_Repair', 'S_Repair_Detail', ''),
    ('Btn_S_IT', 'S_IT_Detail', ''),
    ('Btn_S_Video', 'S_Video_Detail', ''),
    ('S_Repair_Detail', 'Btn_D1', 'Заказать'),
    ('S_IT_Detail', 'Btn_D2', 'Заказать'),
    ('S_Video_Detail', 'Btn_D3', 'Заказать'),
    ('Btn_D1', 'Diag_Menu', ''),
    ('Btn_D2', 'Diag_Menu', ''),
    ('Btn_D3', 'Diag_Menu', ''),

    # Диагностика
    ('Diag_Menu', 'Btn_Request_Callback', 'Заказать звонок 📞'),
    ('Btn_Request_Callback', 'Ask_Phone', ''),
    ('Ask_Phone', 'Btn_Share_Contact', 'Отправить номер'),
    ('Ask_Phone', 'Phone_Input_Manual', 'Ввести вручную'),
    ('Btn_Share_Contact', 'Phone_Success', ''),
    ('Phone_Input_Manual', 'Phone_Success', ''),

    # Кабинет и Отзывы
    ('Btn_Cabinet', 'Cab_Msg_Full', ''),
    ('Cab_Msg_Full', 'Btn_Use_Points', 'Использовать баллы'),
    ('Btn_Use_Points', 'Code_Generated', ''),
    ('Code_Generated', 'Btn_Callback_After_Code', 'Заказать обратный звонок 📞'),
    ('Btn_Callback_After_Code', 'Diag_Menu', ''),
    ('Redeem_Done', 'Review_Request', 'Через 24 часа'),
    ('Review_Request', 'Btn_Get_Review_Bonus', 'Оставить отзыв'),
    ('Btn_Get_Review_Bonus', 'Review_Bonus_Menu', ''),
    ('Review_Bonus_Menu', 'Review_Proof', 'Отправка пруфа'),
    ('Review_Proof', 'Review_Received', ''),
    ('Review_Proof', 'Admin_Verify_Review', ''),

    # Контакты
    ('Btn_Contacts', 'Contacts_Msg', ''),

    # Админка
    ('Admin_Start', 'A_Ask_Code', ''),
    ('A_Ask_Code', 'A_Ask_Sum', ''),
    ('A_Ask_Sum', 'A_Preview', ''),
    ('A_Preview', 'Btn_A_Send', 'Подтвердить'),
    ('A_Preview', 'Btn_A_Cancel', 'Отмена'),
    ('Btn_A_Send', 'Client_Confirm_Screen', ''),
    ('Client_Confirm_Screen', 'Btn_C_Confirm', 'Подтвердить'),
    ('Client_Confirm_Screen', 'Btn_C_Cancel', 'Отклонить'),
    ('Btn_C_Confirm', 'Redeem_Done', ''),
    ('Admin_Verify_Review', 'Btn_Verify_Approve', 'Одобрить'),
    ('Admin_Verify_Review', 'Btn_Verify_Reject', 'Отклонить')
]

class MiroExporter:
    def __init__(self):
        self.node_map = {}

    def create_shape(self, text, node_id, style_key, x, y, w=300, h=120):
        style = STYLES.get(style_key, STYLES['msg'])
        data = {
            "data": {"content": text.replace('\n', '<br>'), "shape": style['shape']},
            "style": {"fillColor": style['color'], "borderColor": style['border'], "borderWidth": "2.0", "textAlign": "center"},
            "position": {"x": x, "y": y},
            "geometry": {"width": w, "height": h}
        }
        res = requests.post(BASE_URL, headers=HEADERS, json=data)
        if res.status_code == 201: return res.json()['id']
        return None

    def create_connector(self, start_id, end_id, label=""):
        data = {"startItem": {"id": start_id}, "endItem": {"id": end_id}, "captions": [{"content": label}] if label else []}
        requests.post(CONNECTOR_URL, headers=HEADERS, json=data)

    def run(self):
        print(f"Экспорт {len(NODES)} узлов...")
        mapping = {}
        for node_id, node_data in NODES.items():
            text, style, x, y, w, h = node_data
            miro_id = self.create_shape(text, node_id, style, x, y, w, h)
            if miro_id:
                self.node_map[node_id] = miro_id
                mapping[miro_id] = node_id
            time.sleep(0.3)
        
        with open('memory/miro_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)

        print(f"Экспорт {len(EDGES)} связей...")
        for start, end, label in EDGES:
            if start in self.node_map and end in self.node_map:
                self.create_connector(self.node_map[start], self.node_map[end], label)
                time.sleep(0.3)
        print("Готово!")

if __name__ == "__main__":
    MiroExporter().run()
