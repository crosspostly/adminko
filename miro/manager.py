import requests
import json
import time
import os
import sys
import re

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID
from utils import clean_miro_text, extract_tag, fuzzy_match # Импортируем из utils

# Пути к файлам
SNAPSHOT_PATH = 'memory/miro_snapshot.json'
MAPPING_FILE = 'memory/miro_mapping.json'
GRAPH_FILE = 'memory/miro_graph.json'


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
            try:
                res = requests.get(url, headers=self.headers)
                res.raise_for_status() # Проверяем на ошибки HTTP
                data = res.json()
                shapes.extend(data.get('data', []))
                cursor = data.get('cursor')
                if not cursor: break
            except requests.exceptions.RequestException as e:
                print(f"[MiroSync] Error fetching shapes: {e}")
                return [], []
            time.sleep(0.2)

        # Загрузка коннекторов (Connectors)
        connectors = []
        cursor = None
        while True:
            url = f"{self.api_base}/connectors?limit=50"
            if cursor: url += f"&cursor={cursor}"
            try:
                res = requests.get(url, headers=self.headers)
                res.raise_for_status()
                data = res.json()
                connectors.extend(data.get('data', []))
                cursor = data.get('cursor')
                if not cursor: break
            except requests.exceptions.RequestException as e:
                print(f"[MiroSync] Error fetching connectors: {e}")
                return shapes, [] # Возвращаем фигуры, если были, но коннекторы не удалось получить
            time.sleep(0.2)

        return shapes, connectors

    def create_snapshot(self):
        """Создает текущий снимок доски (Shapes + Connectors) и граф переходов."""
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
        
        mapping = self.load_mapping()
        if mapping:
            graph = self.build_graph(mapping, snapshot['items'], snapshot['connectors'])
            snapshot['graph'] = graph # Добавляем граф в снимок
        else:
            print("[MiroSync] Mapping file not found or empty. Cannot build graph.")
            snapshot['graph'] = {}
        
        return snapshot

    def build_graph(self, mapping, items, connectors):
        """Строит граф переходов на основе маппинга и коннекторов."""
        graph = {}
        
        # Определение типов по цветам Miro
        COLOR_TYPES = {
            '#f9f1ff': 'msg',   # Фиолетовый
            '#e1f5fe': 'btn',   # Голубой
            '#ffe0b2': 'alert', # Оранжевый
            '#fff9c4': 'logic'  # Желтый/Ромб
        }
        
        # Helper to get var_name or fallback to ID
        def get_block_key(miro_id):
            if not miro_id: return None
            
            # 1. Проверяем, есть ли уже в маппинге
            if miro_id in mapping:
                return mapping[miro_id]
            
            # 2. Проверяем, есть ли тег {#...} в самом тексте блока на доске
            item_data = items.get(miro_id)
            if item_data:
                from utils import extract_tag
                tag, _ = extract_tag(item_data.get('text', ''))
                if tag:
                    mapping[miro_id] = tag # Сразу обновляем маппинг в памяти
                    return tag
            
            # 3. Фаллбэк: используем сам Miro ID как ключ
            return f"ID_{miro_id}"

        for conn_id, conn_data in connectors.items():
            start_id = conn_data.get('start')
            end_id = conn_data.get('end')
            label = conn_data.get('label', '')

            start_key = get_block_key(start_id)
            end_key = get_block_key(end_id)

            if start_key and end_key:
                if start_key not in graph:
                    graph[start_key] = {"transitions": {}}
                
                # Добавляем тип начального блока на основе цвета
                start_item = items.get(start_id, {})
                color = start_item.get('fillColor')
                graph[start_key]['type'] = COLOR_TYPES.get(color, 'msg')

                # Если на стрелке есть текст — это кнопка
                if label:
                    graph[start_key]["transitions"][label] = end_key
                else:
                    # Пустая стрелка = автопереход (специальный ключ)
                    graph[start_key]["transitions"]['_auto_next_'] = end_key
        
        # Сохраняем обновленный маппинг, если в нем появились новые связи
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
            
        return graph

    def save_snapshot(self, snapshot):
        """Сохраняет снимок доски."""
        os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
        with open(SNAPSHOT_PATH, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        print(f"[MiroSync] Snapshot saved to {SNAPSHOT_PATH}")

    def load_snapshot(self):
        """Загружает снимок доски."""
        if os.path.exists(SNAPSHOT_PATH):
            with open(SNAPSHOT_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def load_mapping(self):
        """Загружает маппинг из файла."""
        if os.path.exists(MAPPING_FILE):
            with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def save_graph(self, graph):
        """Сохраняет граф переходов в файл."""
        os.makedirs(os.path.dirname(GRAPH_FILE), exist_ok=True)
        with open(GRAPH_FILE, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print(f"[MiroSync] Graph saved to {GRAPH_FILE}")

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

        old_items = old.get('items', {})
        new_items = new.get('items', {})
        old_conn = old.get('connectors', {})
        new_conn = new.get('connectors', {})

        # Сравнение элементов (Shapes)
        for item_id, item_data in new_items.items():
            if item_id not in old_items:
                diff["added_items"].append({"id": item_id, "data": item_data})
            elif item_data.get('text') != old_items[item_id].get('text'):
                diff["changed_items"].append({
                    "id": item_id, 
                    "old_text": old_items[item_id].get('text'), 
                    "new_text": item_data.get('text')
                })

        for item_id in old_items:
            if item_id not in new_items:
                diff["removed_items"].append({"id": item_id, "data": old_items[item_id]})

        # Сравнение коннекторов
        for cid, cdata in new_conn.items():
            if cid not in old_conn:
                diff["added_connectors"].append({"id": cid, "data": cdata})
            elif cdata.get('start') != old_conn[cid].get('start') or \
                 cdata.get('end') != old_conn[cid].get('end') or \
                 cdata.get('label') != old_conn[cid].get('label'):
                diff["changed_connectors"].append({"id": cid, "old": old_conn[cid], "new": cdata})

        for cid in old_conn:
            if cid not in new_conn:
                diff["removed_connectors"].append({"id": cid, "data": old_conn[cid]})

        return diff

if __name__ == "__main__":
    if not all([MIRO_ACCESS_TOKEN, MIRO_BOARD_ID]):
        print("Error: MIRO_ACCESS_TOKEN or MIRO_BOARD_ID not set in config.")
        sys.exit(1)

    syncer = MiroSync(MIRO_ACCESS_TOKEN, MIRO_BOARD_ID)
    
    print("Creating Miro snapshot and graph...")
    current_snapshot = syncer.create_snapshot()
    
    if current_snapshot:
        syncer.save_snapshot(current_snapshot)
        if 'graph' in current_snapshot and current_snapshot['graph']:
            syncer.save_graph(current_snapshot['graph'])
        else:
            print("[MiroSync] No graph data found in snapshot. Graph file not saved.")
    else:
        print("[MiroSync] Failed to create snapshot.")
