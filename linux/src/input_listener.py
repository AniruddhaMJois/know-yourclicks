"""Linux kernel evdev input event reader using pure Python standard library.

Reads /dev/input/event* directly via struct.unpack without requiring external C extensions.
Enforces the Hardware Privacy Whitelist:
- ONLY Spacebar, Backspace, Delete, and Punctuation marks are processed.
- Letters (A-Z) and numbers (0-9) are immediately discarded.
"""

import os
import glob
import struct
import select
import threading
from typing import List, Optional, Dict, Any
from .config import EV_KEY, KEY_PRESS, SCANCODE_NAMES, ALLOWED_SCANCODES
from .privacy_filter import PrivacyFilter
from .db import Database
from .speed_tracker import SpeedTracker

# struct input_event for 64-bit Linux:
# timeval (16 bytes: 8s + 8us), __u16 type (2 bytes), __u16 code (2 bytes), __s32 value (4 bytes)
EVENT_FORMAT = "qqHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)


class InputListener:
    """Monitors keyboard devices with strict privacy filtering."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(InputListener, cls).__new__(cls)
                cls._instance._init_listener()
            return cls._instance

    def _init_listener(self):
        self.db = Database()
        self.speed_tracker = SpeedTracker()
        self.privacy_filter = PrivacyFilter()
        self.running = False
        self.threads: List[threading.Thread] = []
        self._active_devices: set = set()
        self._supervisor_thread: Optional[threading.Thread] = None
        self.status_info: Dict[str, Any] = {
            "active": False,
            "monitored_devices": [],
            "permission_error": False,
            "message": "Not started"
        }

    def has_active_devices(self) -> bool:
        """Returns True if at least one hardware device is actively monitored."""
        return len(self._active_devices) > 0

    def find_keyboard_devices(self) -> List[str]:
        """Detects keyboard event devices from /proc/bus/input/devices."""
        devices = []
        try:
            with open("/proc/bus/input/devices", "r") as f:
                content = f.read()

            sections = content.strip().split("\n\n")
            for section in sections:
                lines = section.split("\n")
                handlers = ""
                name = ""
                for line in lines:
                    if line.startswith("N: Name="):
                        name = line.split("=", 1)[1].strip('"')
                    elif line.startswith("H: Handlers="):
                        handlers = line.split("=", 1)[1]

                # Check if device is a keyboard
                if "kbd" in handlers and "event" in handlers:
                    for token in handlers.split():
                        if token.startswith("event"):
                            dev_path = f"/dev/input/{token}"
                            if os.path.exists(dev_path):
                                devices.append((dev_path, name))
        except Exception:
            # Fallback to scanning /dev/input/event*
            for dev in glob.glob("/dev/input/event*"):
                devices.append((dev, "Generic Input Device"))

        return [d[0] for d in devices]

    def start(self):
        """Starts monitoring keyboard devices with background supervisor thread."""
        if self.running:
            return

        self.running = True
        self._scan_and_attach_devices()

        # Start supervisor loop to auto-detect newly plugged keyboards or late permission grants
        self._supervisor_thread = threading.Thread(target=self._supervisor_loop, daemon=True)
        self._supervisor_thread.start()

    def _scan_and_attach_devices(self):
        """Scans for available keyboard devices and launches threads for unmonitored ones."""
        device_paths = self.find_keyboard_devices()
        perm_error = False

        for dev_path in device_paths:
            if dev_path in self._active_devices:
                continue

            try:
                # Test opening device
                test_fd = os.open(dev_path, os.O_RDONLY | os.O_NONBLOCK)
                os.close(test_fd)

                t = threading.Thread(target=self._read_device_loop, args=(dev_path,), daemon=True)
                t.start()
                self.threads.append(t)
            except PermissionError:
                perm_error = True
            except Exception:
                pass

        if self._active_devices:
            self.status_info = {
                "active": True,
                "monitored_devices": sorted(list(self._active_devices)),
                "permission_error": False,
                "message": f"Hardware listener active on {len(self._active_devices)} keyboard device(s)."
            }
        elif perm_error:
            self.status_info = {
                "active": False,
                "monitored_devices": [],
                "permission_error": True,
                "message": (
                    "Direct /dev/input access requires hardware permissions. "
                    "Run './install.sh' to automatically configure udev rules, or add user to 'input' group."
                )
            }
        else:
            self.status_info = {
                "active": False,
                "monitored_devices": [],
                "permission_error": False,
                "message": "Waiting for accessible keyboard input devices..."
            }

    def _supervisor_loop(self):
        """Periodic watchdog scanning for device additions or permission changes."""
        import time
        while self.running:
            time.sleep(2.5)
            if not self.running:
                break
            try:
                self._scan_and_attach_devices()
            except Exception:
                pass

    def _read_device_loop(self, dev_path: str):
        """
        Resilient event loop reading from an individual event device.
        Inner try-except prevents single-event errors or transient exceptions from killing the thread.
        """
        try:
            fd = os.open(dev_path, os.O_RDONLY)
            self._active_devices.add(dev_path)
            self.status_info["active"] = True
            self.status_info["monitored_devices"] = sorted(list(self._active_devices))
            self.status_info["message"] = f"Hardware listener active on {len(self._active_devices)} keyboard device(s)."
        except Exception:
            return

        try:
            while self.running:
                try:
                    # Non-blocking wait for event data (timeout 0.5s allows checking self.running)
                    r, _, _ = select.select([fd], [], [], 0.5)
                    if not r:
                        continue

                    data = os.read(fd, EVENT_SIZE)
                    if not data or len(data) < EVENT_SIZE:
                        # EOF or device disconnected
                        break

                    sec, usec, ev_type, code, value = struct.unpack(EVENT_FORMAT, data)

                    # Only process Key Press events (value == 1)
                    if ev_type == EV_KEY and value == KEY_PRESS:
                        # STRICT PRIVACY FILTER:
                        # Drops any alphanumeric or unallowed key immediately!
                        filtered = self.privacy_filter.filter_scancode(code)
                        if filtered:
                            key_name, category = filtered
                            self.db.record_key_press(key_name, category)
                            self.speed_tracker.record_key(key_name, category)
                except (BlockingIOError, InterruptedError):
                    continue
                except (OSError, IOError):
                    # Device unplugged or handle revoked
                    break
                except Exception:
                    # Do NOT kill the thread on transient parsing errors!
                    continue
        finally:
            self._active_devices.discard(dev_path)
            try:
                os.close(fd)
            except Exception:
                pass
            if not self._active_devices:
                self.status_info["active"] = False
                self.status_info["monitored_devices"] = []
                self.status_info["message"] = "No keyboard devices actively connected."

    def dispatch_software_key(self, key_name: str, char_val: str = "", force: bool = False) -> Optional[Dict[str, str]]:
        """
        Processes a key event triggered via the UI or software bridge.
        Enforces identical privacy filtering:
        - Only Space, Backspace, Delete, and Punctuation are counted.
        - Letters and digits are ignored.
        - Avoids double-counting if hardware listener is already tracking the physical device.
        """
        filtered = self.privacy_filter.filter_key_string(key_name, char_val)
        if filtered:
            clean_name, category = filtered
            # If hardware listener is already monitoring active keyboard devices,
            # evdev already captures the physical key. Only write to DB via software
            # if hardware monitoring is unavailable or if explicitly forced.
            if not self.has_active_devices() or force:
                self.db.record_key_press(clean_name, category)

            # Update live speed tracker session if active
            self.speed_tracker.record_key(clean_name, category)
            return {"key": clean_name, "category": category}
        return None

    def stop(self):
        """Stops the hardware listener threads and supervisor."""
        self.running = False
        self._active_devices.clear()
        self.threads.clear()
        self.status_info["active"] = False
        self.status_info["message"] = "Stopped"

    def get_status(self) -> Dict[str, Any]:
        """Returns listener operational status."""
        return self.status_info
