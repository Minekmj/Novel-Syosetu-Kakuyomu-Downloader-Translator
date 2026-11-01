import importlib
import pkgutil
from pathlib import Path
from .base import BaseAiModel, AiResponse

_pkg_dir = Path(__file__).resolve().parent
for _, _module_name, _is_pkg in pkgutil.iter_modules([str(_pkg_dir)]):
    if not _is_pkg and not _module_name.startswith("_") and _module_name != "base":
        importlib.import_module(f"{__name__}.{_module_name}")

__all__ = ["BaseAiModel", "AiResponse"]