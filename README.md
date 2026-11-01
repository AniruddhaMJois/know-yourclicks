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

## 📁 Platform Implementations

* 🐧 **[Linux Application](linux/)** (Complete):
  - Native standalone GTK desktop app window (100% offline), desktop launcher `.desktop`, app grid icon, evdev hardware whitelist, systemd background daemon.
  - Distribution archive: [`linux/knowyourclicks-linux.tar.gz`](linux/knowyourclicks-linux.tar.gz).
  - Architecture spec: [`linux/IMPLEMENTATION_PLAN.md`](linux/IMPLEMENTATION_PLAN.md).
* 🪟 **[Windows Application](windows/)** (Complete):
  - Win32 `WH_KEYBOARD_LL` low-level hook, virtual key whitelist, `SendInput` Unicode expansion, registry autostart, Web GUI dashboard.
  - Distribution archive: [`windows/knowyourclicks-windows.zip`](windows/knowyourclicks-windows.zip).
  - Architecture spec: [`windows/IMPLEMENTATION_PLAN.md`](windows/IMPLEMENTATION_PLAN.md).
* 🍏 **[macOS Implementation Plan](macos/IMPLEMENTATION_PLAN.md)**:
  - CoreGraphics Event Taps (`CGEventTapCreate`), Cocoa `NSStatusItem` Menu Bar agent, and Accessibility permissions.
