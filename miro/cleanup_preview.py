import json
import os
import requests
import sys

# Добавляем корень проекта
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID

def cleanup_miro():
    snapshot_path = 'memory/miro_snapshot.json'
    if not os.path.exists(snapshot_path):
        print("Snapshot missing.")
        return

    with open(snapshot_path, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    items = snapshot.get('items', {})
    
    # Группируем по "похожести" текста (очень грубо)
    # Мы знаем из анализа, что ID 3458764660813... - старые
    # ID 3458764660814... - новые
    
    to_delete = []
    for item_id in items:
        if item_id.startswith('3458764660813'):
            to_delete.append(item_id)
            
    print(f"Found {len(to_delete)} old items to delete.")
    
    confirm = input(f"Proceed with deleting {len(to_delete)} items from Miro? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    headers = {
        'Authorization': f'Bearer {MIRO_ACCESS_TOKEN}',
        'Accept': 'application/json'
    }

    for item_id in to_delete:
        url = f"https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/items/{item_id}"
        res = requests.delete(url, headers=headers)
        if res.status_code == 204:
            print(f"Deleted {item_id}")
        else:
            print(f"Failed to delete {item_id}: {res.status_code}")

if __name__ == "__main__":
    # Поскольку я агент, я не могу ждать ввода 'y/n'. 
    # Я просто выведу список и предложу это сделать.
    pass
