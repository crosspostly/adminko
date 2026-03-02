import sys
import os
import json

# Добавляем корень проекта
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID
from miro.manager import MiroSync

def check():
    syncer = MiroSync(MIRO_ACCESS_TOKEN, MIRO_BOARD_ID)
    
    print("🔍 Сканирую доску Miro...")
    old_snap = syncer.load_snapshot()
    new_snap = syncer.create_snapshot()
    
    if not old_snap:
        print("❌ Старый снимок не найден. Не с чем сравнивать. Сохраняю текущее состояние как базу.")
        syncer.save_snapshot(new_snap)
        return

    diff = syncer.get_diff(old_snap, new_snap)
    
    # 1. Новые блоки (Shapes)
    if diff['added_items']:
        print(f"\n✅ НАЙДЕНЫ НОВЫЕ БЛОКИ ({len(diff['added_items'])}):")
        for item in diff['added_items']:
            text = item['data'].get('text', '').replace('<p>', '').replace('</p>', '')
            print(f"  ID: {item['id']} | Текст: {text[:100]}...")
    else:
        print("\nНовых блоков не обнаружено.")

    # 2. Новые связи (Connectors)
    if diff['added_connectors']:
        print(f"\n🔗 НАЙДЕНЫ НОВЫЕ СВЯЗИ ({len(diff['added_connectors'])}):")
        for conn in diff['added_connectors']:
            start_id = conn['data'].get('start')
            end_id = conn['data'].get('end')
            label = conn['data'].get('label', 'без названия')
            print(f"  Связь {conn['id']}: [{start_id}] --({label})--> [{end_id}]")
    else:
        print("Новых связей не обнаружено.")

    # 3. Изменения текста
    if diff['changed_items']:
        print(f"\n📝 ИЗМЕНЕНИЯ ТЕКСТА ({len(diff['changed_items'])}):")
        for item in diff['changed_items']:
            print(f"  Блок {item['id']}:")
            old_txt = item['old_text'].replace('<p>', '').replace('</p>', '')
            new_txt = item['new_text'].replace('<p>', '').replace('</p>', '')
            print(f"    БЫЛО: {old_txt[:50]}...")
            print(f"    СТАЛО: {new_txt[:50]}...")

    if any(diff.values()):
        print("\n💡 Что будем делать с этими изменениями?")
    else:
        print("\nДоска Miro не изменилась с момента последнего снимка.")

if __name__ == "__main__":
    check()
