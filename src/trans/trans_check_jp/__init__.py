import sys
from . import config
from .config import trans_ai

from .constants import (
    JP_RANGES,
    JP_CHECK_RANGES,
    KO_RANGES,
    JP_PATTERN,
    KO_PATTERN,
    JP_BLOCK_PATTERN,
    WORD_TOKEN_PATTERN,
    WORD_BRACKET_PATTERN,
    EXPLANATION_PATTERNS,
    KO_PARTICLES,
    PARTICLE_PATTERN,
    FAST_LEXICON_REPLACEMENTS,
    KANA_TO_HANGUL,
)
from .hangul_utils import (
    CHOSUNG,
    JUNGSUNG,
    JONGSUNG,
    decompose_hangul,
    compose_hangul,
    attach_jongsung,
)
from .text_cleaner import (
    has_japanese,
    resolve_arrows_and_memos,
    resolve_brackets_from_raw,
    clean_explanation_residue,
    strip_korean_particles,
    sanitize_dot_addition,
    sanitize_translated_word,
    fix_japanese_interjections,
    fix_embedded_katakana,
)
from .translator import (
    call_translator_safely,
    smart_translate,
)
from .widgets import (
    SEMI_TRANS_BTN_STYLE,
    bind_height_sync,
    SuspiciousPatternHighlighter,
    AutoResizingTextEdit,
)
from .workers import (
    GlossaryExtractWorker,
    JapaneseTranslateWorker,
)
from .glossary_dialog import JapaneseGlossaryDialog
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