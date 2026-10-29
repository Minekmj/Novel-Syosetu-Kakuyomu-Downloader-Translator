import json
import os
import re


def extract_title(path):
    try:
        if path.lower().endswith('.txt'):
            with open(path, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline().strip()

            if first_line and set(first_line) == {"="}:
                first_line = os.path.basename(os.path.dirname(path))

            return first_line

        if path.lower().endswith('.json'):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, dict):
                for key in ['title', 'name', 'novel_title', 'work_title']:
                    value = data.get(key)

                    if not isinstance(value, str):
                        continue

                    value = value.strip()

                    if not value:
                        continue

                    while value.endswith('_복원'):
                        value = value[:-len('_복원')].rstrip()

                    match = re.search(r'_\d+\s*~\s*\d+$', value)

                    if match:
                        value = value[:match.start()].rstrip()

                    return value

    except Exception:
        pass

    return ''