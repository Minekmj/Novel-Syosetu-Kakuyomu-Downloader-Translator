import sys
from . import config
from .config import trans_ai

from .check_dialog import JapaneseCheckDialog

_CONFIG_VARS = {'trans_ai'}


class _TransCheckJpModule(sys.modules[__name__].__class__):
    def __getattr__(self, name):
        if name in _CONFIG_VARS:
            return getattr(config, name)
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    def __setattr__(self, name, value):
        if name in _CONFIG_VARS:
            setattr(config, name, value)
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _TransCheckJpModule