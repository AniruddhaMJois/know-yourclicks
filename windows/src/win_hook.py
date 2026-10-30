"""Windows Low-Level Keyboard Hook (WH_KEYBOARD_LL) implementation with strict privacy whitelist.

Strict Privacy Enforcement:
- Only Space, Backspace, Delete, and Punctuation marks are intercepted and tracked.
- All alphanumeric keys (A-Z, 0-9) and credentials are dropped immediately.
- Implemented with ctypes and native Win32 APIs (SetWindowsHookExW, GetMessageW, SendInput).
- Cross-platform safe: provides clean fallback on non-Windows environments for automated testing.
"""

import sys
import threading
from typing import Optional, Dict, Any
from .privacy_filter import PrivacyFilter
from .db import Database
from .speed_tracker import SpeedTracker

# Win32 Constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_BACK = 0x08
VK_SPACE = 0x20

is_windows = sys.platform == "win32"

if is_windows:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # Set up 64-bit compatible ULONG_PTR
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        ULONG_PTR = ctypes.c_ulonglong
    else:
        ULONG_PTR = ctypes.c_ulong

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", wintypes.DWORD),
            ("scanCode", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR)
        ]

    # Hook callback type
    HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    # Win32 SendInput Structures
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR)
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [
            ("type", wintypes.DWORD),
            ("union", INPUT_UNION)
        ]


class WindowsInputListener:
    """Manages the Windows Low-Level Keyboard Hook with strict privacy filtering."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WindowsInputListener, cls).__new__(cls)
                cls._instance._init_listener()
            return cls._instance

    def _init_listener(self):
        self.db = Database()
        self.speed_tracker = SpeedTracker()
        self.privacy_filter = PrivacyFilter()
        self.running = False
        self.hook_thread: Optional[threading.Thread] = None
        self.hook_handle = None
        self._hook_proc_ref = None  # Prevent garbage collection of callback
        self.thread_id = None
        self.status_info: Dict[str, Any] = {
            "active": False,
            "platform": sys.platform,
            "message": "Not started"
        }

    def start(self):
        """Starts the Windows low-level keyboard hook thread."""
        if self.running:
            return

        self.running = True

        if not is_windows:
            self.status_info = {
                "active": True,
                "platform": sys.platform,
                "message": "Running in software emulation mode (Non-Windows platform)"
            }
            return

        self.hook_thread = threading.Thread(target=self._run_hook_loop, daemon=True)
        self.hook_thread.start()
        self.status_info = {
            "active": True,
            "platform": "win32",
            "message": "WH_KEYBOARD_LL active with strict privacy filter."
        }

    def _run_hook_loop(self):
        """Native Win32 hook and message loop."""
        if not is_windows:
            return

        try:
            self.thread_id = kernel32.GetCurrentThreadId()

            def hook_callback(nCode, wParam, lParam):
                if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    kb_struct = KBDLLHOOKSTRUCT.from_address(lParam)
                    vk_code = kb_struct.vkCode

                    # STRICT PRIVACY FILTER:
                    # Evaluates only whitelisted keys (Space, Backspace, Delete, Punctuation)
                    # All alphanumeric keys (0x41-0x5A, 0x30-0x39) return None and are DROPPED!
                    filtered = self.privacy_filter.filter_vk_code(vk_code)
                    if filtered:
                        key_name, category = filtered
                        self.db.record_key_press(key_name, category)
                        self.speed_tracker.record_key(key_name, category)

                return user32.CallNextHookEx(self.hook_handle, nCode, wParam, lParam)

            self._hook_proc_ref = HOOKPROC(hook_callback)
            self.hook_handle = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL,
                self._hook_proc_ref,
                kernel32.GetModuleHandleW(None),
                0
            )

            if not self.hook_handle:
                self.status_info["active"] = False
                self.status_info["message"] = f"Failed to set WH_KEYBOARD_LL hook: error {kernel32.GetLastError()}"
                return

            # Win32 Message Loop
            msg = wintypes.MSG()
            while self.running:
                bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if bRet <= 0:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        except Exception as e:
            self.status_info["active"] = False
            self.status_info["message"] = f"Hook loop error: {e}"
        finally:
            if self.hook_handle:
                user32.UnhookWindowsHookEx(self.hook_handle)
                self.hook_handle = None

    def stop(self):
        """Stops the low-level hook and unregisters the hook procedure."""
        self.running = False
        if is_windows and self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
        self.status_info["active"] = False
        self.status_info["message"] = "Stopped"

    def dispatch_software_key(self, key_name: str, char_val: str = "") -> Optional[Dict[str, str]]:
        """
        Processes a key event triggered via the UI or software bridge.
        Enforces identical privacy filtering:
        - Only Space, Backspace, Delete, and Punctuation are counted.
        - Letters and digits are ignored.
        """
        filtered = self.privacy_filter.filter_key_string(key_name, char_val)
        if filtered:
            clean_name, category = filtered
            self.db.record_key_press(clean_name, category)
            self.speed_tracker.record_key(clean_name, category)
            return {"key": clean_name, "category": category}
        return None

    def get_status(self) -> Dict[str, Any]:
        """Returns listener operational status."""
        return self.status_info

    @staticmethod
    def simulate_expansion(backspaces: int, replacement_text: str):
        """
        Simulates system-wide typing expansion via Win32 SendInput.
        Sends Backspaces to remove shortcut abbreviation + space, then types expanded text + space.
        """
        if not is_windows:
            return

        inputs = []

        # 1. Backspaces (down + up)
        for _ in range(backspaces):
            # Down
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.union.ki = KEYBDINPUT(wVk=VK_BACK, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)
            inputs.append(inp_down)
            # Up
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.union.ki = KEYBDINPUT(wVk=VK_BACK, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
            inputs.append(inp_up)

        # 2. Replacement text characters via KEYEVENTF_UNICODE + Trailing space
        full_text = replacement_text + " "
        for char in full_text:
            code = ord(char)
            # Down
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.union.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)
            inputs.append(inp_down)
            # Up
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.union.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
            inputs.append(inp_up)

        n_inputs = len(inputs)
        arr = (INPUT * n_inputs)(*inputs)
        user32.SendInput(n_inputs, arr, ctypes.sizeof(INPUT))
