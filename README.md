# KnowYourClicks

A privacy-focused, cross-platform keystroke cadence analyzer, shortcut expander, and typing speed monitor that runs entirely locally with zero cloud dependencies.

---

## 🔒 Privacy Architecture

By design, **letters and numbers (A–Z, 0–9) are never sensed, buffered, or stored globally**.

The background listener operates strictly on an immutable hardware whitelist:
* **Spacebar**: Used for word boundary counting, cadence, and triggering shortcut expansions.
* **Punctuation Marks**: (`.`, `,`, `!`, `?`, `;`, `:`, `'`, `"`, `-`, etc.) Used for punctuation distribution statistics and sentence structure analysis.
* **Editing Keys**: (`Backspace`, `Delete`) Used to track typing correction rates and error ratios.
* **Alphanumerics & Credentials**: **Immediately dropped** at the OS driver/hook level.

---

## 🚀 Key Features

1. **Space-Triggered Text Expander**:
   - Create custom shortcuts (e.g., `idk` ➔ `i dont know`).
   - Triggered upon pressing the **Spacebar** in the typing screen (or system-wide via virtual injection).
2. **On-Demand Typing Speed Tracker**:
   - Configurable countdown timer: **30s**, **60s**, **90s**, **120s**.
   - **Mode 1 (Given Text)**: Interactive typing test screen with prompt passages, real-time WPM, CPM, and accuracy %.
   - **Mode 2 (Background)**: Passive measurement in the background across any application using space/punctuation rhythm without recording content.
3. **Local-Only Analytics (Zero Cloud)**:
   - Stored in a local SQLite database on your device.
   - Breakdown reports for: **1 Hour**, **1 Day**, **1 Week**, **1 Month / All-time**.
4. **Persistent Background Execution**:
   - Runs seamlessly when the main app window is closed via System Tray / Menu Bar / System Daemon.

---

## 📁 Platform Implementation Plans

Individual platform architectures and OS-level hook specifications are detailed in their respective directories:

* 🐧 **[Linux Implementation Plan](linux/IMPLEMENTATION_PLAN.md)**: Evdev scancode whitelist, `/dev/uinput` expansion, Systemd user service, and Ayatana AppIndicator.
* 🪟 **[Windows Implementation Plan](windows/IMPLEMENTATION_PLAN.md)**: Win32 `WH_KEYBOARD_LL` low-level hook filter, `SendInput` Unicode injection, and `Shell_NotifyIconW` tray.
* 🍏 **[macOS Implementation Plan](macos/IMPLEMENTATION_PLAN.md)**: CoreGraphics Event Taps (`CGEventTapCreate`), Cocoa `NSStatusItem` Menu Bar agent, and Accessibility permissions.
