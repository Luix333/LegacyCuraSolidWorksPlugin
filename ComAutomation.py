# Copyright (c) 2026 CuraSolidWorksPlugin contributors
# CuraSolidWorksPlugin is released under the terms of the LGPLv3 or higher.

"""Minimal late-bound COM automation on top of the bundled comtypes.

SolidWorks' automation objects do not return type information from IDispatch::GetTypeInfo, so comtypes can only wrap
them "fully dynamically". In that mode reading an attribute already invokes it: ``app.RevisionNumber`` returns the
string, ``app.RevisionNumber()`` fails, and a bare ``app.ExitApp`` quits SolidWorks. ComObject avoids the guessing by
making every access explicit: call() invokes a method, get()/set() read and write a property.

Import this module from the main thread (the plugin does so in register()): comtypes initialises COM for the thread
that first imports it and uninitialises it again from an atexit handler, which only balances out on the main thread.
Worker threads call initializeComForThread() themselves.
"""

import ctypes
import ctypes.wintypes
import os
import sys
import threading

_THIRD_PARTY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thirdparty")
if _THIRD_PARTY_PATH not in sys.path:
    sys.path.append(_THIRD_PARTY_PATH)

import comtypes  # noqa: E402
import comtypes.client  # noqa: E402  Imported here so VARIANT results can be wrapped from any thread later on.
from comtypes.automation import IDispatch, DISPATCH_METHOD, DISPATCH_PROPERTYGET, DISPATCH_PROPERTYPUT  # noqa: E402

COMError = comtypes.COMError

_thread_state = threading.local()


def initializeComForThread() -> None:
    """Initialise COM for the calling thread, once per thread.

    It is deliberately never uninitialised again: Cura's job workers are long-lived threads, and releasing a COM
    pointer after its thread's CoUninitialize() is the kind of thing that crashes long after the fact.
    """

    if getattr(_thread_state, "initialized", False):
        return
    try:
        comtypes.CoInitializeEx(comtypes.COINIT_APARTMENTTHREADED)
    except OSError:
        # RPC_E_CHANGED_MODE: somebody already made this thread multi-threaded. COM is usable either way.
        pass
    _thread_state.initialized = True


def _unwrap(value):
    if isinstance(value, ComObject):
        return value._pointer
    return value


class ComObject:
    """An IDispatch pointer with explicit method/property access."""

    def __init__(self, pointer) -> None:
        # comtypes hands out IDispatch results wrapped in its dynamic _Dispatch class; keep the raw pointer.
        self._pointer = getattr(pointer, "_comobj", pointer)
        self._dispids = {}

    @classmethod
    def create(cls, prog_id: str) -> "ComObject":
        """CoCreateInstance by ProgID. Out-of-process servers such as SolidWorks may hand out a running instance."""

        clsid = comtypes.GUID.from_progid(prog_id)
        return cls(comtypes.CoCreateInstance(clsid, interface = IDispatch, clsctx = comtypes.CLSCTX_LOCAL_SERVER))

    def _dispid(self, name: str) -> int:
        dispid = self._dispids.get(name)
        if dispid is None:
            dispid = self._pointer.GetIDsOfNames(name)[0]
            self._dispids[name] = dispid
        return dispid

    @staticmethod
    def _wrap(result):
        if result is not None and hasattr(result, "_comobj"):
            return ComObject(result)
        return result

    def call(self, name: str, *args):
        """Invoke method ``name``. IDispatch results come back as ComObject, a null object as None."""

        result = self._pointer.Invoke(self._dispid(name), *[_unwrap(arg) for arg in args], _invkind = DISPATCH_METHOD)
        return self._wrap(result)

    def get(self, name: str):
        return self._wrap(self._pointer.Invoke(self._dispid(name), _invkind = DISPATCH_PROPERTYGET))

    def set(self, name: str, value) -> None:
        self._pointer.Invoke(self._dispid(name), _unwrap(value), _invkind = DISPATCH_PROPERTYPUT)

    def release(self) -> None:
        """Drop the reference now, on the calling thread, instead of whenever the garbage collector gets to it."""

        self._pointer = None
        self._dispids = {}


_TH32CS_SNAPPROCESS = 0x00000002
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.wintypes.DWORD),
                ("cntUsage", ctypes.wintypes.DWORD),
                ("th32ProcessID", ctypes.wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", ctypes.wintypes.DWORD),
                ("cntThreads", ctypes.wintypes.DWORD),
                ("th32ParentProcessID", ctypes.wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.wintypes.DWORD),
                ("szExeFile", ctypes.c_wchar * ctypes.wintypes.MAX_PATH)]


def findProcessIds(executable_name: str) -> set:
    """IDs of the processes in the current Windows session whose executable is called ``executable_name``."""

    kernel32 = ctypes.WinDLL("kernel32", use_last_error = True)
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.DWORD]
    kernel32.Process32FirstW.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
    kernel32.Process32NextW.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
    kernel32.ProcessIdToSessionId.argtypes = [ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]

    def sessionOf(pid):
        session = ctypes.wintypes.DWORD()
        if kernel32.ProcessIdToSessionId(pid, ctypes.byref(session)):
            return session.value
        return None

    own_session = sessionOf(os.getpid())
    found = set()
    snapshot = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == _INVALID_HANDLE_VALUE:
        return found
    try:
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        more = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            if entry.szExeFile.lower() == executable_name.lower() and sessionOf(entry.th32ProcessID) == own_session:
                found.add(entry.th32ProcessID)
            more = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return found
