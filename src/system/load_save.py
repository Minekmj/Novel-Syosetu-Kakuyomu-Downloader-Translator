import os
import json
import time
import queue
import threading
from src.system.config import DATA_FILE

_save_queue = queue.Queue()

def load_data(src=DATA_FILE):
    if os.path.exists(src):
        try:
            with open(src, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"데이터 로드 실패 ({src}): {e}")
    
    if src == DATA_FILE:
        return {"src": "", "list": {}}
    return {}

def save_data(data, src=DATA_FILE):
    try:
        with open(src, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"데이터 저장 실패 ({src}): {e}")

def _set_nested_value(data_dict, keys, value):
    if isinstance(keys, (str, int)):
        data_dict[keys] = value
        return

    current = data_dict
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def save_data_add(data_src, value, src=DATA_FILE):
    _save_queue.put((src, data_src, value))

def _save_worker():
    while True:
        try:
            item = _save_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        batch = {item[0]: [(item[1], item[2])]}
        
        time.sleep(0.05)
        while not _save_queue.empty():
            s, k, v = _save_queue.get_nowait()
            if s not in batch:
                batch[s] = []
            batch[s].append((k, v))
            _save_queue.task_done()

        for file_path, updates in batch.items():
            current_data = load_data(file_path)
            for keys, val in updates:
                _set_nested_value(current_data, keys, val)
            save_data(current_data, file_path)

        _save_queue.task_done()

_worker_thread = threading.Thread(target=_save_worker, daemon=True)
_worker_thread.start()