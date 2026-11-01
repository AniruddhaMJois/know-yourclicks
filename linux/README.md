# KnowYourClicks (Linux)

A privacy-first, 100% offline Linux desktop application for keystroke cadence analytics, space-triggered text expansion, and on-demand typing speed measurement.

---

## 🔒 Privacy Guarantee

KnowYourClicks is engineered to protect sensitive credentials, passwords, and private communications:
* **Whitelisted Keys Only**: Intercepts **ONLY** `Spacebar`, `Backspace`, `Delete`, and `Punctuation marks` (`.`, `,`, `!`, `?`, `;`, `:`, `'`, `"`, `-`, `/`, `\`, `[`, `]`, `{`, `}`, `~`, `@`, `#`, `$`, `%`, `^`, `&`, `*`, `+`, `=`, `<`, `>`, `_`).
* **Hardware-Level Alphanumeric Blocking**: Letters (`A–Z`) and numbers (`0–9`) are **immediately dropped at the Linux evdev kernel driver layer**. They are never logged, buffered, or stored.
* **100% Offline & Local Storage**: Runs completely locally with zero internet access. All statistics and shortcuts are stored in local SQLite (`~/.local/share/knowyourclicks/stats.db`). Zero external network requests.

---

## 🚀 Installation & Running

### Step 1: Install the Desktop Application

Run the automated installer:

```bash
./install.sh
```

This will automatically:
1. Install the application files to `~/.local/share/knowyourclicks/app/`.
2. Install the binary symlink to `~/.local/bin/knowyourclicks`.
3. Install high-resolution vector and PNG desktop icons to `~/.local/share/icons/hicolor/`.
4. Install the `.desktop` launcher to `~/.local/share/applications/knowyourclicks.desktop`.
5. Register and start the background systemd monitoring service (`knowyourclicks.service`).

### Step 2: Launch the App

You can now open the app in any of the following ways:
* **Application Menu**: Open your GNOME Application Grid / Search (press <kbd>Super</kbd>) and search for **KnowYourClicks**.
* **Terminal**: Run `knowyourclicks app`
* **Direct Script**: Run `./start.sh`

*(Note: The app launches in a dedicated, native Linux desktop window with full offline controls.)*

---

## 📋 Features

### 1. Dedicated Native Desktop App Window
* Standalone desktop application window powered by PyGObject GTK & WebKit.
* Integrated with GNOME Shell, Fedora, KDE, and Wayland window managers with native window decorations, close/minimize controls, and custom app icon.
* 100% offline: no browser tabs, no URL bar, no external network calls.

### 2. Space-Triggered Shortcut Expander
* Configure custom abbreviations (e.g., `idk` ➔ `i dont know`).
* In the **Typing Screen**, type `idk` and press <kbd>Space</kbd>: the text automatically expands to `i dont know `!
* Includes a full Shortcut Manager to add, modify, or delete shortcuts.

### 3. On-Demand Timed Speed Tracker
* Activated only when triggered (never runs continuously to avoid distorted metrics).
* Selectable countdown timers: **30s**, **60s**, **90s**, **120s**.
* **Mode 1: Try with Given Text**:
  - Interactive typing test with live accuracy %, gross WPM, and net CPM calculations.
* **Mode 2: Measure in the Background (Passive)**:
  - Runs silently in the background while you work in your text editor, terminal, or IDE.
  - Measures typing cadence via space and punctuation rhythm without inspecting characters.
  - Emits a native desktop notification (`notify-send`) when the timer finishes.

### 4. Local Analytics & Statistics (Zero Cloud)
* Filterable timeframes: **1 Hour**, **1 Day**, **1 Week**, **1 Month**, and **All-Time**.
* Metrics:
  - Total whitelisted keystrokes
  - Spacebar presses and minute-by-minute activity timeline
  - Editing activity (Backspaces & Deletes) with correction rate percentage
  - Key distribution frequency meters

### 5. Persistent Background Daemon (Systemd)
The background keystroke service runs continuously via `systemd --user` so tracking continues even when the desktop window is closed.
To check background service status:

```bash
systemctl --user status knowyourclicks.service
```

---

## 🛠️ CLI Reference

```bash
knowyourclicks app          # Launch native desktop application window
knowyourclicks app --browser# Open dashboard in browser instead of desktop window
knowyourclicks start        # Start background daemon
knowyourclicks stop         # Stop background daemon
knowyourclicks restart      # Restart background daemon
knowyourclicks status       # Check daemon PID and listener status
knowyourclicks stats        # Print 24h keystroke summary in terminal
```

---

## ⚙️ Hardware Event Permissions (`/dev/input`)

To enable system-wide background hardware keystroke monitoring without root:

```bash
./setup_permissions.sh
```
*Note: After adding your user to the `input` group, log out and log back in for changes to apply.*

---

## 🗑️ Uninstallation

To cleanly remove the desktop launcher, icons, binary, and background service:

```bash
./uninstall.sh
```
*(Your local statistics database at `~/.local/share/knowyourclicks/stats.db` will remain preserved.)*
