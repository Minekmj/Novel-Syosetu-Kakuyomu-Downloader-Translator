from .base import (
    Sites,
    BaseSite,
    SITES,
    SITE_REGISTRY,
    register_site,
    get_site,
    get_site_name,
    get_search_class,
    site_point_text,
    site_is_kaku,
    site_build_params,
)
from .helpers import normalize_url, ha_set_ui_main
from .narou import NarouBaseSite, NarouSite, MidnightSite, NocturneSite
from .hameln import HamelnBaseSite, HamelnSite, Hameln18Site
from .kakuyomu import KakuyomuSite


def na_set_ui(window, layout):
    SITE_REGISTRY[Sites.NAROU].setup_ui(window, layout)

def ha_set_ui(window, layout):
    SITE_REGISTRY[Sites.HAMELLEUN].setup_ui(window, layout)

def ha18_set_ui(window, layout):
    SITE_REGISTRY[Sites.HAMELLEUN18].setup_ui(window, layout)

def kaku_set_ui(window, layout):
    SITE_REGISTRY[Sites.KAKUYOMU].setup_ui(window, layout)



def na_build_params(window):
    return SITE_REGISTRY[Sites.NAROU].build_params(window)

def ha_build_params(window):
    return SITE_REGISTRY[Sites.HAMELLEUN].build_params(window)

def kaku_build_params(window):
    return SITE_REGISTRY[Sites.KAKUYOMU].build_params(window)