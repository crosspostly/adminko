import argparse
import datetime
import os

CHANGELOG_PATH = os.path.join(os.path.dirname(__file__), '../CHANGELOG.md')

def add_entry(change_type, message):
    """Adds an entry to the Unreleased section of CHANGELOG.md"""
    
    # Маппинг типов на заголовки
    headers = {
        'added': '### Added',
        'changed': '### Changed',
        'fixed': '### Fixed',
        'removed': '### Removed'
    }
    
    target_header = headers.get(change_type.lower())
    if not target_header:
        print(f"Error: Unknown change type '{change_type}'. Use: added, changed, fixed, removed.")
        return

    with open(CHANGELOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Ищем секцию [Unreleased]
    unreleased_index = -1
    for i, line in enumerate(lines):
        if "## [Unreleased]" in line:
            unreleased_index = i
            break
    
    if unreleased_index == -1:
        # Если нет Unreleased, создаем (обычно после заголовка файла)
        # Предполагаем, что заголовок занимает первые строки
        lines.insert(4, "
## [Unreleased]
")
        unreleased_index = 5

    # Ищем нужный подзаголовок (например, ### Added) ВНУТРИ Unreleased
    # (до следующего заголовка ## или конца файла)
    header_index = -1
    insertion_index = -1
    
    # Сканируем только до следующего релиза
    for i in range(unreleased_index + 1, len(lines)):
        line = lines[i].strip()
        if line == target_header:
            header_index = i
            insertion_index = i + 1
            break
        if line.startswith("## ") and "Unreleased" not in line: # Наткнулись на следующую версию (например ## 1.0.0)
            break

    # Если подзаголовка нет, создаем его сразу после Unreleased
    if header_index == -1:
        lines.insert(unreleased_index + 1, f"{target_header}
- {message}

")
        print(f"Created new section '{target_header}' and added entry.")
    else:
        lines.insert(insertion_index, f"- {message}
")
        print(f"Added entry to existing '{target_header}' section.")

    with open(CHANGELOG_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def main():
    parser = argparse.ArgumentParser(description="Auto-updater for CHANGELOG.md")
    parser.add_argument("type", choices=['added', 'changed', 'fixed', 'removed'], help="Type of change")
    parser.add_argument("message", help="Description of the change")
    
    args = parser.parse_args()
    add_entry(args.type, args.message)

if __name__ == "__main__":
    main()
