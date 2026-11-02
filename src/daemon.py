"""Background daemon process management for KnowYourClicks (Linux).

Manages:
- Hardware input listener thread
- Local HTTP REST server thread
- PID file tracking and clean termination
- Background fork / systemd execution mode
"""

import os
import sys
import time
import signal
import threading
from pathlib import Path
from .config import PID_FILE, LOG_FILE, DEFAULT_HOST, DEFAULT_PORT
from .input_listener import InputListener
from .server import run_server


def get_running_pid() -> int:
    """Returns PID if daemon is running, else 0."""
    if not PID_FILE.exists():
        return 0
    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process is alive
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError, ProcessLookupError):
        # Stale PID file
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return 0


def start_daemon(foreground: bool = False, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Starts the background daemon services."""
    existing_pid = get_running_pid()
    if existing_pid:
        print(f"[KnowYourClicks] Daemon is already running (PID: {existing_pid}).")
        return

    if not foreground:
        # Fork into background
        pid = os.fork()
        if pid > 0:
            # Parent returns
            print(f"[KnowYourClicks] Daemon started in background with PID: {pid}")
            return

        # Child process: decouple environment
        os.setsid()
        # Second fork to prevent acquiring controlling terminal
        pid2 = os.fork()
        if pid2 > 0:
            sys.exit(0)

        # Redirect standard file descriptors to log file
        sys.stdout.flush()
        sys.stderr.flush()
        with open(LOG_FILE, "a") as log:
            os.dup2(log.fileno(), sys.stdout.fileno())
            os.dup2(log.fileno(), sys.stderr.fileno())

    # Write PID
    current_pid = os.getpid()
    PID_FILE.write_text(str(current_pid))

    from .db import Database
    db = Database()
    listener = InputListener()
    listener.start()

    def signal_handler(signum, frame):
        listener.stop()
        try:
            db.close()
        except Exception:
            pass
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        run_server(host=host, port=port)
    finally:
        listener.stop()
        try:
            db.close()
        except Exception:
            pass
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass


def stop_daemon():
    """Stops the running background daemon."""
    pid = get_running_pid()
    if not pid:
        print("[KnowYourClicks] Daemon is not currently running.")
        return

    print(f"[KnowYourClicks] Stopping daemon (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        print("[KnowYourClicks] Daemon stopped successfully.")
    except Exception as e:
        print(f"[KnowYourClicks] Error stopping daemon: {e}")
    finally:
        PID_FILE.unlink(missing_ok=True)


def daemon_status():
    """Prints current status of the background daemon."""
    pid = get_running_pid()
    if pid:
        print(f"Status: RUNNING (PID: {pid})")
        print(f"Log file: {LOG_FILE}")
        print(f"Web Dashboard: http://127.0.0.1:{DEFAULT_PORT}/")
    else:
        print("Status: STOPPED")
