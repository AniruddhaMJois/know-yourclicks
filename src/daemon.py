"""Background process and service lifecycle management for KnowYourClicks (Windows).

Manages:
- Win32 Low-Level Keyboard Hook
- Local HTTP REST server thread
- PID file tracking and clean termination
- Background detachment via pythonw.exe or subprocess flags
- Windows Autostart registry integration
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from .config import PID_FILE, LOG_FILE, DEFAULT_HOST, DEFAULT_PORT
from .win_hook import WindowsInputListener
from .server import run_server

is_windows = sys.platform == "win32"


def get_running_pid() -> int:
    """Returns PID if daemon is running, else 0."""
    if not PID_FILE.exists():
        return 0
    try:
        pid = int(PID_FILE.read_text().strip())
        # Check process status
        if is_windows:
            # Check with tasklist on Windows
            cmd = f'tasklist /FI "PID eq {pid}"'
            out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            if str(pid) in out:
                return pid
            else:
                PID_FILE.unlink(missing_ok=True)
                return 0
        else:
            os.kill(pid, 0)
            return pid
    except Exception:
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return 0


def start_daemon(foreground: bool = False, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Starts the Windows background daemon."""
    existing_pid = get_running_pid()
    if existing_pid:
        print(f"[KnowYourClicks] Background service is already running (PID: {existing_pid}).")
        return

    if not foreground:
        # Launch detached background process
        current_script = Path(__file__).resolve().parent.parent / "knowyourclicks.py"
        
        # Prefer pythonw.exe on Windows for windowless execution
        py_exe = sys.executable
        if is_windows and "python.exe" in py_exe.lower():
            pythonw = Path(py_exe).parent / "pythonw.exe"
            if pythonw.exists():
                py_exe = str(pythonw)

        creationflags = 0
        if is_windows:
            creationflags = (
                getattr(subprocess, "DETACHED_PROCESS", 0x00000008) |
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200) |
                getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            )

        with open(LOG_FILE, "a") as log_out:
            proc = subprocess.Popen(
                [py_exe, str(current_script), "start", "--foreground"],
                stdout=log_out,
                stderr=log_out,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                close_fds=not is_windows
            )
            print(f"[KnowYourClicks] Background service started with PID: {proc.pid}")
            return

    # Foreground worker mode (runs hook and server)
    PID_FILE.write_text(str(os.getpid()))

    listener = WindowsInputListener()
    listener.start()

    def signal_handler(signum, frame):
        listener.stop()
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    except Exception:
        pass

    try:
        run_server(host=host, port=port)
    finally:
        listener.stop()
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass


def stop_daemon():
    """Stops the running Windows daemon process."""
    pid = get_running_pid()
    if not pid:
        print("[KnowYourClicks] Background service is not currently running.")
        return

    print(f"[KnowYourClicks] Stopping background service (PID: {pid})...")
    try:
        if is_windows:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            os.kill(pid, signal.SIGTERM)
            for _ in range(20):
                time.sleep(0.1)
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
        print("[KnowYourClicks] Background service stopped successfully.")
    except Exception as e:
        print(f"[KnowYourClicks] Error stopping service: {e}")
    finally:
        PID_FILE.unlink(missing_ok=True)


def daemon_status():
    """Prints current status of the Windows background service."""
    pid = get_running_pid()
    if pid:
        print(f"Status: RUNNING (PID: {pid})")
        print(f"Log file: {LOG_FILE}")
        print(f"Web Dashboard: http://127.0.0.1:{DEFAULT_PORT}/")
    else:
        print("Status: STOPPED")


def install_autostart():
    """Configures Windows autostart on login via HKCU Run registry key."""
    if not is_windows:
        print("Autostart registry configuration is supported on Windows.")
        return

    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "KnowYourClicks"
    
    script_path = Path(__file__).resolve().parent.parent / "knowyourclicks.py"
    py_exe = sys.executable
    pythonw = Path(py_exe).parent / "pythonw.exe"
    if pythonw.exists():
        py_exe = str(pythonw)

    command = f'"{py_exe}" "{script_path}" start --foreground'

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
        print(f"[KnowYourClicks] Autostart successfully registered in Windows Registry: {app_name}")
    except Exception as e:
        print(f"[KnowYourClicks] Failed to configure registry autostart: {e}")


def uninstall_autostart():
    """Removes Windows autostart registry entry."""
    if not is_windows:
        return

    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "KnowYourClicks"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, app_name)
        print(f"[KnowYourClicks] Autostart successfully removed from Windows Registry: {app_name}")
    except FileNotFoundError:
        print("[KnowYourClicks] Autostart entry was not registered.")
    except Exception as e:
        print(f"[KnowYourClicks] Error removing registry key: {e}")
