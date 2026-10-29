import sys
from .dialog import NovelRecommendDialog
from . import card

def __getattr__(name: str):
    if name == "detail_ui":
        return card.detail_ui
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __setattr__(name: str, value):
    if name == "detail_ui":
        card.detail_ui = value
    super(sys.modules[__name__].__class__, sys.modules[__name__]).__setattr__(name, value)