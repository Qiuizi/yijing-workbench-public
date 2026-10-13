"""Current-user protected storage for local API credentials on Windows."""

from __future__ import annotations

import base64
import ctypes
import sys
from ctypes import wintypes


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _transform(value: bytes, *, protect: bool) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("API 密钥安全保存目前仅支持 Windows 用户级 DPAPI")
    crypt32 = ctypes.WinDLL("Crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32", use_last_error=True)
    source_buffer = ctypes.create_string_buffer(value)
    source = _DataBlob(len(value), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = _DataBlob()
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    function.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR if protect else ctypes.POINTER(wintypes.LPWSTR),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), "易经起卦工作台" if protect else None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(target.pbData)


def protect(api_key: str) -> str:
    protected = _transform(api_key.encode("utf-8"), protect=True)
    return base64.b64encode(protected).decode("ascii")


def unprotect(encoded: str | None) -> str | None:
    if not encoded:
        return None
    protected = base64.b64decode(encoded, validate=True)
    return _transform(protected, protect=False).decode("utf-8")
