import time
import json
import os
import re
import sys
import subprocess

# Добавляем корень проекта
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID
from miro.manager import MiroSync

MAPPING_FILE = os.path.join(os.path.dirname(__file__), '../memory/miro_mapping.json')
TEXTS_FILE = os.path.join(os.path.dirname(__file__), '../texts.py')

def clean_miro_text(text):
    """Очищает текст от оберток Miro (<p>), но оставляет полезные теги."""
    if not text: return ""
    # Miro часто оборачивает все в <p>...</p>
    if text.startswith("<p>") and text.endswith("</p>"):
        text = text[3:-4]
    return text

def update_python_file(file_path, variable_name, new_value):
    """
    Обновляет значение переменной в файле texts.py.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Экранируем для Python строки
    safe_value = new_value.replace('"', '\"').replace('\n', '\\n')
    
    # Регулярка ищет VAR = "..." или VAR = (...)
    # (?s) включает DOTALL (точка матчит переводы строк)
    pattern = r'({}\s*=\s*)(['"\(].*?)(?=
[A-Z_]|

|\Z)'.format(variable_name)
    
    match = re.search(pattern, content, re.DOTALL)
    if match:
        current_val_raw = match.group(2)
        # Грубая проверка: если "новое значение" уже содержится в "старом сыром" (с учетом кавычек)
        # лучше перезаписать, чтобы быть уверенным.
        
        new_assignment = f'{variable_name} = "{safe_value}"'
        
        # Если мы заменяем то же самое на то же самое, файл не меняется
        # Но у нас current_val_raw может быть в скобках.
        # Поэтому просто формируем новый контент и сравниваем строки.
        
        new_content = content.replace(match.group(0), new_assignment)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
            
    return False

def restart_bot():
    print("[AutoSync] Restarting bot process...")
    try:
        # Ищем процесс, запущенный через venv/bin/python bot.py
        # Используем pkill для надежности
        subprocess.run(['pkill', '-f', 'bot.py'])
        print("[AutoSync] Sent kill signal to bot. Systemd should restart it.")
    except Exception as e:
        print(f"[AutoSync] Error restarting bot: {e}")

def run_sync_loop():
    print("[AutoSync] Started. Polling Miro every 30s...")
    syncer = MiroSync(MIRO_ACCESS_TOKEN, MIRO_BOARD_ID)
    
    while True:
        try:
            if not os.path.exists(MAPPING_FILE):
                print("[AutoSync] Mapping file missing. Waiting...")
                time.sleep(30)
                continue
                
            with open(MAPPING_FILE, 'r') as f:
                mapping = json.load(f)

            shapes = syncer.get_all_shapes()
            # Словарь {MiroID: Text}
            miro_data = {s['id']: clean_miro_text(s['data'].get('content', '')) for s in shapes}

            changes_made = False

            for miro_id, var_name in mapping.items():
                if miro_id in miro_data:
                    new_text = miro_data[miro_id]
                    # Пытаемся обновить. Функция вернет True только если файл реально изменился.
                    if update_python_file(TEXTS_FILE, var_name, new_text):
                        print(f"[AutoSync] Updated {var_name} from Miro.")
                        changes_made = True

            if changes_made:
                print("[AutoSync] Changes detected and applied.")
                restart_bot()
            else:
                pass # Тишина в эфире, изменений нет

        except Exception as e:
            print(f"[AutoSync] Error: {e}")
        
        time.sleep(30)

if __name__ == "__main__":
    run_sync_loop()
