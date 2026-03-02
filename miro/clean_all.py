import requests
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID

HEADERS = {
    'Authorization': f'Bearer {MIRO_ACCESS_TOKEN}',
    'Accept': 'application/json'
}

def clean_board():
    print("Fetching all items to delete...")
    url = f"https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/items?limit=50"
    items_to_delete = []
    
    while url:
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            break
        data = res.json()
        for item in data.get('data', []):
            items_to_delete.append(item['id'])
        
        cursor = data.get('cursor')
        if cursor:
            url = f"https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/items?limit=50&cursor={cursor}"
        else:
            url = None
            
    print(f"Found {len(items_to_delete)} items. Deleting...")
    for item_id in items_to_delete:
        requests.delete(f"https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/items/{item_id}", headers=HEADERS)
        time.sleep(0.2)
        
    print("Board cleaned!")

if __name__ == "__main__":
    clean_board()
