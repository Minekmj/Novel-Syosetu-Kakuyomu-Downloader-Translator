import json
import requests

from src.system.src import get_resource_path

http_session = requests.Session()

TAG_CATEGORIES = json.load(open(get_resource_path("find/tag.json"), encoding="UTF-8"))

from src.find.site.kakuyoumu_calss import KakuyomuSearch
from src.find.site.narow_class import NaroSearch
from src.find.site.midnight_class import MidnightSearch
from src.find.site.nocturne_calss import NocturneSearch
from src.find.site.syosetu_class import SyosetuSearch
from src.find.site.syosetu18_class import SyosetuSearch18