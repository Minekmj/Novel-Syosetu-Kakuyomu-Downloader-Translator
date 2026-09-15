COOKIES = {
}

BASE_HEADERS = {
}

import os
import json
import src.find.state as sf

def reset(b):
    if b:
        sf.find_cf()
    global COOKIES
    global BASE_HEADERS
    if os.path.exists(sf.SRC):
        with open(sf.SRC, "r", encoding="UTF-8") as f:
            g = json.load(f)
            BASE_HEADERS = g["headers"]
            COOKIES =  { "cf_clearance": g["cookies"][0]["value"] }
            
def reset_b():
    global COOKIES
    global BASE_HEADERS
    if os.path.exists(sf.SRC):
        with open(sf.SRC, "r", encoding="UTF-8") as f:
            g = json.load(f)
            BASE_HEADERS = g["headers"]
            COOKIES =  { "cf_clearance": g["cookies"][0]["value"] }

reset(False)