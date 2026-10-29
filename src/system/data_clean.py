import os
import json
from cryptography.fernet import Fernet

from src.system.config import *

class Data_set:
    def __init__(self, data: dict):
        self.data = data
        self.src = ""
        self.data_dict = {}
        
    def set_src(self, src: str):
        self.src = src
        self.data_dict[self.src] = {}
    
    def get_data(self, data_name: str, data_type):
        self.data_dict[self.src][data_name] = self.data.get(data_name, data_type)
        try:
            type_s = type(data_type)
            if type_s == str or type_s == int or type_s == float:
                os.environ[f"minedown_setting_{data_name}"] = str(self.data_dict[self.src][data_name])
        except:
            pass
        
    def get_data_api(self, data_name: str, key_path: str):
        raw_val = self.data.get(data_name, "")
        
        if not raw_val:
            self.data_dict[self.src][data_name] = ""
            return

        if isinstance(raw_val, list):
            raw_str = json.dumps(raw_val, ensure_ascii=False)
        else:
            raw_str = str(raw_val)

        if not os.path.exists(key_path):
            key_dir = os.path.dirname(key_path)
            if key_dir and not os.path.exists(key_dir):
                os.makedirs(key_dir, exist_ok=True)
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
        else:
            with open(key_path, "rb") as f:
                key = f.read().strip()

        fernet = Fernet(key)
        encrypted_val = fernet.encrypt(raw_str.encode("utf-8")).decode("utf-8")
        
        self.data_dict[self.src][data_name] = encrypted_val


def data_clean(data: dict):
    d = Data_set(data)
    
    d.set_src(DATA_FILE_SYSTEM)
    d.get_data("src", "./out/")
    d.get_data("theme", "LAVENDER")
    d.get_data("change_no_mark", False)
    d.get_data("RAW_TEXT", False)
    d.get_data("AI_PROMPT", "")
    d.get_data("origin_name", False)
    d.get_data("CENSOR_ADVANCED", False)
    d.get_data("CENSOR_SHUFFLE", False)
    d.get_data("CENSOR_MODE", "word")
    d.get_data("CENSOR_PAPAGO", False)
    
    d.set_src(DATA_FILE_LIST)
    d.get_data("list", {})
    
    d.set_src(DATA_FILE_TRANS)
    d.get_data("translate_model", "gemini-3.5-flash-lite")
    d.get_data("translate_rpm", 15)
    d.get_data("translate_temperature", 0.5)
    d.get_data("translate_concurrency", 10)
    d.get_data("translate_max_chars", 10000)
    d.get_data("pre", {})
    d.get_data("translate_models", [])
    d.get_data("translate_br_start", 0)
    d.get_data("translate_glossary_enabled", True)
    d.get_data("translate_isno_x", False)
    d.get_data("translate_thinking_budget", "기본값")
    
    d.set_src(DATA_FILE_EPUB)
    d.get_data("epub_data", {})
    
    d.set_src(DATA_FILE_V)
    d.get_data("V", "")
    
    d.set_src(DATA_FILE_SITE)
    d.get_data("hameln18_flags_main", {})
    d.get_data("hameln_flags_main", {})
    
    d.set_src(DATA_FILE_DICT)
    d.get_data("dictionary", {})
    
    api_val = data.get("api", "")
    api_keys_val = data.get("api_keys", [])
    if not api_keys_val and api_val:
        data["api_keys"] = [api_val]

    d.set_src(DATA_FILE_API)
    d.get_data_api("api", KEY_FILE_PATH)
    d.get_data_api("api_keys", KEY_FILE_PATH)
    d.get_data("api_index", 0)
    
    return d.data_dict


class Read_data:
    def __init__(self):
        self.data = {}
    
    def get_path(self, src: str):
        if os.path.exists(src):
            with open(src, "r", encoding="utf-8") as f:
                self.data.update(json.load(f))
    
    def get_path_api(self, src: str, key_path: str):
        if not os.path.exists(src):
            return
            
        if not os.path.exists(key_path):
            return

        with open(key_path, "rb") as kf:
            key = kf.read().strip()
            
        fernet = Fernet(key)

        with open(src, "r", encoding="utf-8") as f:
            api_data = json.load(f)

        decrypted_dict = {}
        for k, v in api_data.items():
            if isinstance(v, str) and v.startswith("gAAAAA"):
                try:
                    dec = fernet.decrypt(v.encode("utf-8")).decode("utf-8")
                    if k == "api_keys" or (dec.startswith("[") and dec.endswith("]")):
                        try:
                            decrypted_dict[k] = json.loads(dec)
                        except Exception:
                            decrypted_dict[k] = dec
                    else:
                        decrypted_dict[k] = dec
                except Exception:
                    decrypted_dict[k] = v
            else:
                decrypted_dict[k] = v

        self.data.update(decrypted_dict)


def data_get():
    d = Read_data()
    
    d.get_path(DATA_FILE_SYSTEM)
    d.get_path(DATA_FILE_LIST)
    d.get_path(DATA_FILE_TRANS)
    d.get_path(DATA_FILE_EPUB)
    d.get_path(DATA_FILE_V)
    d.get_path(DATA_FILE_SITE)
    d.get_path(DATA_FILE_DICT)
    
    d.get_path_api(DATA_FILE_API, KEY_FILE_PATH)
    
    return d.data