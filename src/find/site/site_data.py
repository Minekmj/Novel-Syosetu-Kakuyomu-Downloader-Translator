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
            try:
                COOKIES =  { "cf_clearance": g["cf_clearance"]["value"] }
            except:
                COOKIES =  { }
            
def reset_b():
    global COOKIES
    global BASE_HEADERS
    if os.path.exists(sf.SRC):
        with open(sf.SRC, "r", encoding="UTF-8") as f:
            g = json.load(f)
            BASE_HEADERS = g["headers"]
            try:
                COOKIES =  { "cf_clearance": g["cf_clearance"]["value"] }
            except:
                COOKIES =  { }

reset(False)