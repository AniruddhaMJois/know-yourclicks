# KnowYourClicks (Windows)

A privacy-first keystroke analytics engine, space-triggered text expander, and on-demand typing speed monitor designed natively for Microsoft Windows.

---

## 🔒 Privacy Guarantee

KnowYourClicks is engineered from the ground up to protect passwords, private chats, and sensitive credentials:
* **Whitelisted Keys Only**: Senses **ONLY** `Spacebar`, `Backspace`, `Delete`, and `Punctuation marks` (`.`, `,`, `!`, `?`, `;`, `:`, `'`, `"`, `-`, `/`, `\`, `[`, `]`, `{`, `}`, `~`, `@`, `#`, `$`, `%`, `^`, `&`, `*`, `+`, `=`, `<`, `>`, `_`).
* **Hardware/Hook Alphanumeric Blocking**: All letters (`A–Z`) and numbers (`0–9`) are **immediately dropped at the Win32 `WH_KEYBOARD_LL` low-level hook callback**. They are never logged, buffered, or stored in memory or disk.
* **100% Local Storage**: All statistics and shortcuts are stored strictly in local SQLite (`%LOCALAPPDATA%\KnowYourClicks\stats.db`). Zero cloud dependencies, zero external network requests.

---

## 🚀 Quick Start (Windows)

Double-click `start.bat` or run from Command Prompt / PowerShell:

```cmd
start.bat
```

Or using the CLI tool:

```cmd
python knowyourclicks.py app
```

The Web Dashboard will launch automatically in your default browser at `http://127.0.0.1:45678/`.

---

## 📋 Core Features

### 1. Space-Triggered Shortcut Expander
* Configure shortcuts in the UI or CLI (e.g. `idk` ➔ `i dont know`).
* In the **Typing Screen** (and globally across Windows apps): typing `idk` followed by <kbd>Space</kbd> replaces `idk ` with `i dont know `!
* Shortcut Manager allows adding, modifying, and deleting abbreviations anytime.

### 2. On-Demand Timed Speed Tracker
* Activated only when triggered (never runs continuously in the background to avoid distorted metrics while browsing).
* Selectable durations: **30s**, **60s**, **90s**, **120s**.
* **Mode 1: Try with Given Text (In-App)**:
  - Interactive typing test with prompt passages, real-time WPM, CPM, accuracy %, and error counts.
* **Mode 2: Measure in the Background**:
  - Runs silently in the background while you work in Microsoft Word, VS Code, Notepad, Browser, or Slack.
  - Measures typing cadence via space and punctuation rhythm without inspecting characters.
  - Fires a native Windows Toast Notification when the session completes.

### 3. Local Analytics & Statistics (Zero Cloud)
* Filterable timeframes: **1 Hour**, **1 Day**, **1 Week**, **1 Month**, and **All-Time**.
* Metrics:
  - Total whitelisted keystrokes
  - Spacebar presses and activity timeline
  - Editing activity (Backspaces & Deletes) with correction rate percentage
  - Key distribution frequency meters

### 4. Background Service Persistence
The service continues running in the background when the dashboard browser tab is closed.
To configure KnowYourClicks to autostart silently on Windows boot/login:

```cmd
install_autostart.bat
```
*(Registers under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\KnowYourClicks`. To remove, run `uninstall_autostart.bat`.)*

---

## 🛠️ CLI Reference

```cmd
python knowyourclicks.py app                  # Start service & open Web UI in browser
python knowyourclicks.py start                # Start background service
python knowyourclicks.py stop                 # Stop background service
python knowyourclicks.py restart              # Restart background service
python knowyourclicks.py status               # Check service and hook status
python knowyourclicks.py stats                # Print 24h keystroke summary in terminal
python knowyourclicks.py autostart-install    # Add to Windows startup registry
python knowyourclicks.py autostart-uninstall  # Remove from Windows startup registry
```

---

## 📁 Windows Directory Structure

```
windows/
├── knowyourclicks-windows.zip    # 📦 Release distribution package for Windows
├── start.bat                     # Double-clickable launcher
├── stop.bat                      # Double-clickable stop script
├── status.bat                    # Double-clickable status inspector
├── install_autostart.bat         # Configures Windows registry autostart
├── uninstall_autostart.bat       # Removes Windows registry autostart
├── knowyourclicks.bat            # CLI wrapper
├── knowyourclicks.py             # Main entrypoint
├── README.md                     # Documentation
├── IMPLEMENTATION_PLAN.md        # Technical architecture specification
├── src/
│   ├── config.py                 # Paths (%LOCALAPPDATA%) & VK whitelist codes
│   ├── privacy_filter.py         # Virtual-Key and character whitelist filter
│   ├── db.py                     # Local SQLite database manager & aggregation
│   ├── text_expander.py          # Space-triggered shortcut expansion logic
│   ├── speed_tracker.py          # 30/60/90/120s timer & Windows toast notifications
│   ├── win_hook.py               # Win32 WH_KEYBOARD_LL low-level hook & SendInput
│   ├── server.py                 # Embedded HTTP REST API
│   ├── daemon.py                 # Background process management & registry hook
│   └── web/                      # Dark-themed dashboard UI (HTML/CSS/JS)
│       ├── index.html
│       ├── css/style.css
│       └── js/app.js
└── tests/
    └── test_windows_app.py       # Unit & integration test suite (9/9 passing)
```
