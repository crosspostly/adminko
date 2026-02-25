import json
import re
import os
import sys

# Добавляем корень проекта
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import texts

def clean_text(text):
    if not text: return ""
    # Убираем HTML теги
    text = re.sub(r'<[^>]*>', ' ', text)
    # Убираем лишние пробелы и спецсимволы
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def analyze():
    snapshot_path = 'memory/miro_snapshot.json'
    if not os.path.exists(snapshot_path):
        print("Snapshot missing. Run miro/manager.py first.")
        return

    with open(snapshot_path, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    items = snapshot.get('items', {})
    
    bot_texts = {}
    for attr in dir(texts):
        if not attr.startswith("__") and isinstance(getattr(texts, attr), str):
            bot_texts[attr] = clean_text(getattr(texts, attr))

    print(f"--- Miro Analysis (Items: {len(items)}, Bot variables: {len(bot_texts)}) ---")
    
    mapping = {}
    duplicates = []
    orphans = []
    
    for item_id, item_data in items.items():
        miro_text = clean_text(item_data['text'])
        if not miro_text: continue
        
        best_match = None
        best_score = 0
        
        for var_name, var_text in bot_texts.items():
            if miro_text in var_text or var_text in miro_text:
                if len(miro_text) < 10 and miro_text != var_text:
                    continue
                
                score = min(len(miro_text), len(var_text)) / max(len(miro_text), len(var_text))
                if score > best_score:
                    best_score = score
                    best_match = var_name
        
        if best_match:
            if best_match in mapping.values():
                existing_id = [k for k, v in mapping.items() if v == best_match][0]
                duplicates.append({
                    "var": best_match,
                    "existing": {"id": existing_id, "text": items[existing_id]['text'], "x": items[existing_id]['x'], "y": items[existing_id]['y']},
                    "new": {"id": item_id, "text": item_data['text'], "x": item_data['x'], "y": item_data['y']}
                })
            else:
                mapping[item_id] = best_match
        else:
            orphans.append({"id": item_id, "text": item_data['text'], "x": item_data['x'], "y": item_data['y']})

    print("\n[!] DUPLICATES FOUND:")
    for d in duplicates:
        print(f"  Variable: {d['var']}")
        print(f"    - Block 1: ID={d['existing']['id']}, Pos=({d['existing']['x']}, {d['existing']['y']})")
        print(f"    - Block 2: ID={d['new']['id']}, Pos=({d['new']['x']}, {d['new']['y']})")
        if len(d['new']['text']) > len(d['existing']['text']):
            print(f"    => SUGGESTION: Keep Block 2, Delete Block 1")
        else:
            print(f"    => SUGGESTION: Keep Block 1, Delete Block 2")

    print("\n[?] ORPHANS:")
    for o in orphans:
        if len(clean_text(o['text'])) > 5:
            print(f"  - ID={o['id']}, Text='{o['text'][:50]}...'")

    print(f"\n[+] Total mapping suggested: {len(mapping)} items.")
    with open('memory/miro_mapping_suggested.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    analyze()
