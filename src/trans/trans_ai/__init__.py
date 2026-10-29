import sys
from . import config
from .config import (
    API,
    MODEL_NAME,
    CUSTOM_AI_PROMPT,
    USE_ADVANCED_CENSOR,
    CENSOR_SHUFFLE,
    CENSOR_EXTRACT_MODE,
    CENSOR_PAPAGO,
    IMG_TAG_PATTERN,
    set_api_key,
    rest,
    client,
)

from .novel_translator import TransAi_All
from .json_translator import TransAi_From_Json

_CONFIG_VARS = {
    'API',
    'MODEL_NAME',
    'CUSTOM_AI_PROMPT',
    'USE_ADVANCED_CENSOR',
    'CENSOR_SHUFFLE',
    'CENSOR_EXTRACT_MODE',
    'CENSOR_PAPAGO',
    'client',
}


class _TransAiModule(sys.modules[__name__].__class__):
    def __getattr__(self, name):
        if name in _CONFIG_VARS:
            return getattr(config, name)
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    def __setattr__(self, name, value):
        if name in _CONFIG_VARS:
            setattr(config, name, value)
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _TransAiModule