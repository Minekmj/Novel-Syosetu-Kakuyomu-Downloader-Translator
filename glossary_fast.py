import ctypes
import os
import sys

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DLL_PATH = os.path.join(BASE_DIR, "glossary_fast", "glossary_fast.dll")

_lib = ctypes.CDLL(DLL_PATH)

_lib.glossary_extract_sample.argtypes = [
    ctypes.c_char_p,
    ctypes.c_double
]
_lib.glossary_extract_sample.restype = ctypes.c_void_p

_lib.glossary_free.argtypes = [ctypes.c_void_p]
_lib.glossary_free.restype = None


def extract_glossary_sample(all_text, paserent):
    if not all_text:
        return ""

    try:
        percent = float(paserent)
    except (TypeError, ValueError):
        percent = 10.0

    percent = max(0.1, min(100.0, percent))

    data = all_text.encode("utf-8")

    ptr = _lib.glossary_extract_sample(
        data,
        percent
    )

    if not ptr:
        return ""

    try:
        result = ctypes.string_at(ptr).decode(
            "utf-8",
            errors="replace"
        )
    finally:
        _lib.glossary_free(ptr)

    return result