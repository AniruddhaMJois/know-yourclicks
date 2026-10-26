# KnowYourClicks (Linux)

A privacy-first keystroke analytics engine, space-triggered text expander, and on-demand typing speed monitor for Linux.

---

## 🔒 Privacy Guarantee

KnowYourClicks is engineered to protect sensitive credentials, passwords, and communications:
* **Whitelisted Keys Only**: Intercepts **ONLY** `Spacebar`, `Backspace`, `Delete`, and `Punctuation marks` (`.`, `,`, `!`, `?`, `;`, `:`, `'`, `"`, `-`, etc.).
* **Alphanumerics Blocked**: Letters (`A–Z`) and numbers (`0–9`) are **immediately dropped at the kernel driver layer**. They are never read, buffered, or stored.
* **100% Local Storage**: All statistics and shortcuts are stored strictly in local SQLite (`~/.local/share/knowyourclicks/stats.db`). Zero data ever leaves your machine.

---

## 🚀 Quick Start

To start the background daemon and launch the dashboard:

```bash
./start.sh
```

Or using the CLI tool:

```bash
./knowyourclicks app
```

The web dashboard will open in your default browser at `http://127.0.0.1:45678/`.

---

## 📋 Features

### 1. Space-Triggered Shortcut Expander
* Configure shortcuts in the UI or CLI (e.g. `idk` ➔ `i dont know`).
* In the **Typing Screen**, type `idk` and press **Space**: the abbreviation instantly expands to `i dont know `!

### 2. On-Demand Typing Speed Tracker
* Activated only when triggered (never runs continuously in the background to avoid skewed data).
* Selectable countdown timers: **30s**, **60s**, **90s**, **120s**.
* **Mode 1: Try with Given Text**:
  - In-app interactive typing test with live accuracy %, gross WPM, and net CPM calculations.
* **Mode 2: Measure in the Background**:
  - Runs silently in the background while you work in your browser, terminal, or IDE.
  - Measures your typing rhythm via space and punctuation cadence without reading text.
  - Emits a native desktop notification (`notify-send`) when the test finishes.

### 3. Local Analytics & Statistics
* Filterable timeframes: **1 Hour**, **1 Day**, **1 Week**, **1 Month**, and **All-Time**.
* Metrics:
  - Total whitelisted keystrokes
  - Spacebar presses and activity timeline
  - Editing activity (Backspaces & Deletes) with correction rate percentage
  - Key distribution frequency meters

### 4. Background Service Persistence
The daemon keeps running in the background even when all browser windows are closed.
To ensure the daemon autostarts on boot:

```bash
./install_service.sh
```

---

## 🛠️ CLI Reference

```bash
./knowyourclicks app          # Start daemon & open Web UI in browser
./knowyourclicks start        # Start background daemon
./knowyourclicks stop         # Stop background daemon
./knowyourclicks restart      # Restart background daemon
./knowyourclicks status       # Check daemon PID and listener status
./knowyourclicks stats        # Print 24h keystroke summary in terminal
```

---

## ⚙️ Hardware Event Permissions (`/dev/input`)

To monitor global keyboard hardware events on Linux without root:

```bash
./setup_permissions.sh
```
*Note: After adding your user to the `input` group, log out and log back in for changes to apply.*
