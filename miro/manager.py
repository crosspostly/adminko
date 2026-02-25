import requests
import json
import time
import os

SNAPSHOT_PATH = 'memory/miro_snapshot.json'

class MiroSync:
    def __init__(self, access_token, board_id):
        self.access_token = access_token
        self.board_id = board_id
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.api_base = f'https://api.miro.com/v2/boards/{self.board_id}'

    def fetch_all_items(self):
        """Сканирует всю доску (shapes + connectors)."""
        shapes = []
        cursor = None
        
        # Загрузка фигур (Shapes)
        while True:
            url = f"{self.api_base}/items?type=shape&limit=50"
            if cursor: url += f"&cursor={cursor}"
            res = requests.get(url, headers=self.headers)
            if res.status_code != 200: break
            data = res.json()
            shapes.extend(data.get('data', []))
            cursor = data.get('cursor')
            if not cursor: break
            time.sleep(0.2)

        # Загрузка коннекторов (Connectors)
        connectors = []
        cursor = None
        while True:
            url = f"{self.api_base}/connectors?limit=50"
            if cursor: url += f"&cursor={cursor}"
            res = requests.get(url, headers=self.headers)
            if res.status_code != 200: break
            data = res.json()
            connectors.extend(data.get('data', []))
            cursor = data.get('cursor')
            if not cursor: break
            time.sleep(0.2)

        return shapes, connectors

    def create_snapshot(self):
        """Создает текущий снимок доски."""
        shapes, connectors = self.fetch_all_items()
        
        snapshot = {
            "timestamp": time.time(),
            "items": {s['id']: {
                "type": s['type'],
                "text": s['data'].get('content', ''),
                "x": s['position'].get('x'),
                "y": s['position'].get('y'),
                "fillColor": s.get('style', {}).get('fillColor')
            } for s in shapes},
            "connectors": {c['id']: {
                "start": c.get('startItem', {}).get('id'),
                "end": c.get('endItem', {}).get('id'),
                "label": c.get('captions', [{}])[0].get('content', '') if c.get('captions') else ''
            } for c in connectors}
        }
        return snapshot

    def save_snapshot(self, snapshot):
        os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
        with open(SNAPSHOT_PATH, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

    def load_snapshot(self):
        if os.path.exists(SNAPSHOT_PATH):
            with open(SNAPSHOT_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_diff(self, old, new):
        """Сравнивает два снапшота и возвращает список изменений."""
        diff = {
            "added_items": [],
            "removed_items": [],
            "changed_items": [],
            "added_connectors": [],
            "removed_connectors": [],
            "changed_connectors": []
        }

        # 1. Сравнение элементов (Shapes)
        old_items = old.get('items', {})
        new_items = new.get('items', {})

        for item_id, item_data in new_items.items():
            if item_id not in old_items:
                diff["added_items"].append({"id": item_id, "data": item_data})
            elif item_data['text'] != old_items[item_id]['text']:
                diff["changed_items"].append({
                    "id": item_id, 
                    "old_text": old_items[item_id]['text'], 
                    "new_text": item_data['text']
                })

        for item_id in old_items:
            if item_id not in new_items:
                diff["removed_items"].append({"id": item_id, "data": old_items[item_id]})

        # 2. Сравнение коннекторов
        old_conn = old.get('connectors', {})
        new_conn = new.get('connectors', {})

        for cid, cdata in new_conn.items():
            if cid not in old_conn:
                diff["added_connectors"].append({"id": cid, "data": cdata})
            elif cdata != old_conn[cid]:
                diff["changed_connectors"].append({"id": cid, "old": old_conn[cid], "new": cdata})

        for cid in old_conn:
            if cid not in new_conn:
                diff["removed_connectors"].append({"id": cid, "data": old_conn[cid]})

        return diff

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID
    
    syncer = MiroSync(MIRO_ACCESS_TOKEN, MIRO_BOARD_ID)
    
    print("Checking for changes in Miro...")
    old_snap = syncer.load_snapshot()
    new_snap = syncer.create_snapshot()
    
    if not old_snap:
        print("First sync. Saving initial snapshot.")
        syncer.save_snapshot(new_snap)
    else:
        diff = syncer.get_diff(old_snap, new_snap)
        
        has_changes = any(diff.values())
        if has_changes:
            print("\n[!] Changes detected in Miro:")
            if diff['changed_items']:
                for item in diff['changed_items']:
                    print(f"  - Changed text in block {item['id']}: '{item['old_text']}' -> '{item['new_text']}'")
            if diff['added_items']:
                print(f"  - Added {len(diff['added_items'])} new blocks.")
            if diff['removed_items']:
                print(f"  - Removed {len(diff['removed_items'])} blocks.")
            
            # В реальном сценарии здесь будет вызов логики обновления бота
            syncer.save_snapshot(new_snap)
        else:
            print("No changes detected.")
