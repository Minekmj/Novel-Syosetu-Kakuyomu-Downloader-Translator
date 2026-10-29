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
    ForceStopException,
    set_api_key,
    rest,
    client,
)
from .rate_limiter import AsyncRateLimiter
from .model_worker import (
    ModelWorker,
    _parse_models,
    _normalize_model_values,
    _create_model_workers,
)
from .chunk_utils import (
    _is_stopped,
    repair_chunk_boundaries,
    adjust_split_mid,
    prepare_output_paths,
)
from .validator import (
    get_ratio_thresholds,
    validate_translation_ratios,
    reset_or_retry_censor,
)
from .runner import run_worker_pool
from .chunk_translator import (
    translate_chunk_safe_async,
    _build_chunk_system_prompt,
)
from .pipeline import (
    TranslationItem,
    run_translation_batch,
)
from .novel_translator import (
    _translate_light_novel_async,
    translate_light_novel,
    TransAi_All,
)
from .json_translator import (
    _TransAi_From_Json_async,
    TransAi_From_Json,
    _parse_json_title_metadata,
)

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