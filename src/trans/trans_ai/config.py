import re
from google import genai
from src.system.load_save import load_data, save_data
from src.trans.trans_ai_utils import glossary_text

API = ''
MODEL_NAME = 'gemini-3.5-flash-lite'
CUSTOM_AI_PROMPT = ''

USE_ADVANCED_CENSOR = False  
CENSOR_SHUFFLE = True  
CENSOR_EXTRACT_MODE = "word"  
CENSOR_PAPAGO = False

IMG_TAG_PATTERN = re.compile(r'-img-:[^\s\r\n]+')


class ForceStopException(Exception):
    pass


def set_api_key(api_key):
    global API, client
    API = api_key.strip() or ''
    client = genai.Client(api_key=API if API != '' else "None")
    glossary_text.client = client
    data = load_data()
    data['api'] = API
    save_data(data)


def rest():
    global API, client
    API = load_data().get('api', '')
    client = genai.Client(api_key=API if API != '' else "None")
    glossary_text.client = client


client = genai.Client(api_key=API if API != '' else "None")
glossary_text.client = client
rest()