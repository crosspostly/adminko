import json
import os
import requests
import sys
import time

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
    connectors = snapshot.get('connectors', {})
    
    # Мы знаем из анализа, что ID 3458764660813... - старые
    to_delete = []
    for item_id in items:
        if item_id.startswith('3458764660813'):
            to_delete.append(item_id)
            
    # Также удаляем коннекторы, связанные со старыми блоками
    conn_to_delete = []
    for cid, cdata in connectors.items():
        if cid.startswith('3458764660813'):
            conn_to_delete.append(cid)
        elif cdata['start'] in to_delete or cdata['end'] in to_delete:
            conn_to_delete.append(cid)

    print(f"Deleting {len(to_delete)} old items and {len(conn_to_delete)} connectors from Miro...")

    headers = {
        'Authorization': f'Bearer {MIRO_ACCESS_TOKEN}',
        'Accept': 'application/json'
    }

    # Удаляем коннекторы первыми
    for cid in conn_to_delete:
        url = f"https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/connectors/{cid}"
        requests.delete(url, headers=headers)
        time.sleep(0.2)

    # Удаляем блоки
    for item_id in to_delete:
        url = f"https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/items/{item_id}"
        requests.delete(url, headers=headers)
        time.sleep(0.2)

    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup_miro()
