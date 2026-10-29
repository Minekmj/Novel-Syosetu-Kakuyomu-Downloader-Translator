import sys
from . import config
from .config import (
    API,
    API_KEYS,
    API_INDEX,
    MODEL_NAME,
    CUSTOM_AI_PROMPT,
    USE_ADVANCED_CENSOR,
    CENSOR_SHUFFLE,
    CENSOR_EXTRACT_MODE,
    CENSOR_PAPAGO,
    IMG_TAG_PATTERN,
    set_api_key,
    set_api_keys,
    set_api_index,
    switch_to_next_api_key,
    switch_api_key_safe,
    set_cooldown,
    get_cooldown_remaining,
    wait_cooldown,
    get_client,
    refresh_client,
    rest,
    client,
    extract_glossary
)

from .novel_translator import TransAi_All
from .json_translator import TransAi_From_Json

_CONFIG_VARS = {
    'API',
    'API_KEYS',
    'API_INDEX',
    'MODEL_NAME',
    'CUSTOM_AI_PROMPT',
    'USE_ADVANCED_CENSOR',
    'CENSOR_SHUFFLE',
    'CENSOR_EXTRACT_MODE',
    'CENSOR_PAPAGO',
    'set_api_key',
    'set_api_keys',
    'set_api_index',
    'switch_to_next_api_key',
    'switch_api_key_safe',
    'set_cooldown',
    'get_cooldown_remaining',
    'wait_cooldown',
    'get_client',
    'refresh_client',
    'rest',
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