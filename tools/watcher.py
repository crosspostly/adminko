import os
import subprocess
import time

def get_git_diff():
    """Returns a list of changed files compared to HEAD."""
    try:
        # Проверяем изменения, которые еще не закоммичены
        diff = subprocess.check_output(['git', 'diff', 'HEAD', '--name-only'], stderr=subprocess.STDOUT).decode('utf-8')
        return diff.splitlines()
    except Exception as e:
        return []

def watch():
    """Background loop to monitor file changes."""
    print("Watcher Agent active. Monitoring /home/varsmana/adminko for changes...")
    
    # Игнорируем сам чейнджлог и логи, чтобы не зациклиться
    ignored_patterns = ['CHANGELOG.md', 'memory/', '__pycache__', '.log']
    
    known_changes = set()
    
    while True:
        diff_files = get_git_diff()
        current_changes = {f for f in diff_files if not any(p in f for p in ignored_patterns)}
        
        if current_changes > known_changes:
            new_files = current_changes - known_changes
            print(f"[!] New unrecorded changes detected in: {', '.join(new_files)}")
            print("Action required: Document these changes in CHANGELOG.md")
            # Здесь в будущем можно добавить вызов LLM API для авто-генерации описания
            
        known_changes = current_changes
        time.sleep(30) # Проверка дважды в минуту

if __name__ == "__main__":
    watch()
