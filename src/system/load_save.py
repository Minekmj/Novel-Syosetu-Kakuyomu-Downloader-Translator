import os
import json

from src.system.data_clean import data_clean, data_get

def load_data(src=""):
    if src != "":
        if os.path.exists(src):
            try:
                with open(src, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"데이터 로드 실패 ({src}): {e}")
            return {}
    else:
        return data_get()

def save_data(data, src=""):
    if src != "":
        try:
            with open(src, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"데이터 저장 실패 ({src}): {e}")
    else:
        d = data_clean(data)
        for s, i in d.items():
            try:
                with open(s, "w", encoding="utf-8") as f:
                    json.dump(i, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"데이터 저장 실패 ({s}): {e}")