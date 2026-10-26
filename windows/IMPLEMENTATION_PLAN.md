# Windows Implementation Plan: KnowYourClicks

## 1. System Overview & Platform Architecture

On Windows, global keyboard monitoring and system tray presence are integrated using native Win32 APIs. The solution consists of a **Low-Level Windows Hook Service** running in the background and a **Client Dashboard GUI**.

```mermaid
flowchart TD
    subgraph WindowsOS ["Windows Operating System"]
        WinHook["Low-Level Keyboard Hook (WH_KEYBOARD_LL)"] -->|Raw VK Codes| PrivacyFilter["Win32 Virtual Key Whitelist Filter"]
        
        subgraph BackgroundWorker ["Background Worker (System Tray / Win32)"]
            PrivacyFilter -->|Allowed: VK_SPACE, VK_BACK, Punctuation| ProcessEngine["Event Counter & Cadence Engine"]
            PrivacyFilter -->|Dropped: A-Z, 0-9, Function Keys| NullSink["Immediate Discard (Zero Logging)"]
            
            ProcessEngine --> SQLiteDB[("Local SQLite (%LOCALAPPDATA%\\KnowYourClicks\\)")]
            ProcessEngine --> SpeedTimer["Background Speed Timer (30/60/90/120s)"]
            
            SendInputAPI["SendInput (Win32)"] <---|Simulate Backspaces + Unicode| ExpanderEngine["Text Expansion Engine"]
        end
        
        subgraph WinUI ["Desktop GUI (Flutter Windows / WPF / WinUI 3)"]
            AnalyticsView["Analytics (1h, 1d, 1w, 1mo)"]
            TypingScreen["Typing Screen & Shortcut Test"]
            GivenTextTest["Interactive Typing Test Screen"]
        end
        
        BackgroundWorker <-->|Named Pipes (\\\\.\\pipe\\knowyourclicks)| WinUI
    end
```

---

## 2. Privacy-First Win32 Hook Whitelist Filter

To strictly enforce:
> *"sense only spacebar, punctuation marks, and backspace and delete keys. others shouldn't be sensed by the app for privacy reasons."*

The Windows background service implements `SetWindowsHookExW` with `WH_KEYBOARD_LL`. The callback `LowLevelKeyboardProc` filters every incoming `KBDLLHOOKSTRUCT.vkCode` against an explicit whitelist.

### Whitelisted Windows Virtual Key Codes
| Category | Virtual Key Constant | Hex Code |
| :--- | :--- | :--- |
| **Space** | `VK_SPACE` | `0x20` |
| **Editing** | `VK_BACK` (Backspace) | `0x08` |
| | `VK_DELETE` (Delete) | `0x2E` |
| **Punctuation** | `VK_OEM_PERIOD` (`.` and `>`) | `0xBE` |
| | `VK_OEM_COMMA` (`,` and `<`) | `0xBC` |
| | `VK_OEM_1` (`;` and `:`) | `0xBA` |
| | `VK_OEM_2` (`/` and `?`) | `0xBF` |
| | `VK_OEM_3` (`` ` `` and `~`) | `0xC0` |
| | `VK_OEM_4` (`[` and `{`) | `0xDB` |
| | `VK_OEM_5` (`\` and `\|`) | `0xDC` |
| | `VK_OEM_6` (`]` and `}`) | `0xDD` |
| | `VK_OEM_7` (`'` and `"`) | `0xDE` |
| | `VK_OEM_MINUS` (`-` and `_`) | `0xBD` |
| | `VK_OEM_PLUS` (`=` and `+`) | `0xBB` |
| **Alphanumerics (0-9, A-Z)** | **BLOCKED & DROPPED** | `CallNextHookEx` immediately without tracking |

Any key press outside this list is immediately forwarded down the hook chain without reading, inspecting, or storing anything into memory.

---

## 3. Features & Logic

### A. Text Expander & Shortcut Option (on Space Key)
* **Typing Screen**:
  - The typing screen maintains an active word buffer.
  - When `VK_SPACE` is intercepted, the preceding word token (e.g., `idk`) is looked up in the `shortcuts` database table.
  - If a match exists, the token is replaced with the full expanded phrase (`i dont know `).
* **System-Wide Expansion (Win32 SendInput)**:
  - If global expansion is enabled, upon detecting `VK_SPACE` following a known shortcut token, the service dispatches `SendInput` events:
    1. Sends $N \times$ `VK_BACK` inputs to erase the typed abbreviation and space.
    2. Sends the expanded text using `KEYEVENTF_UNICODE`.

### B. Timed Typing Speed Tracker
Triggered only upon explicit user request.
* **Duration Options**: `30s`, `60s`, `90s`, `120s`.
* **Option 1: Try with Given Text (In-App)**:
  - Interactive prompt rendered on the typing screen.
  - Computes real-time gross WPM, net WPM, accuracy percentage, and character mistakes.
* **Option 2: Measure in the Background**:
  - Triggered via System Tray context menu or keyboard shortcut (e.g., `Win + Shift + K`).
  - Measures typing speed passively while the user works in Word, VS Code, Slack, or any browser.
  - Privacy-preserving speed calculation:
    $$\text{Words Counted} = \text{Count}(\text{VK\_SPACE}) + \text{Count}(\text{Punctuation Delimiters})$$
    $$\text{WPM} = \frac{\text{Words Counted}}{\text{Elapsed Minutes}}$$
  - Triggers a native Windows Toast Notification with sound when the timer finishes.

### C. Local Analytics & Statistics (Zero Cloud)
* **Storage Location**: `%LOCALAPPDATA%\KnowYourClicks\data.db` (e.g., `C:\Users\<User>\AppData\Local\KnowYourClicks\data.db`).
* **Time Windows**:
  - **1 Hour**: Minute-by-minute keystroke distribution of spaces vs. corrections.
  - **1 Day**: Hourly productivity graph showing busiest typing hours.
  - **1 Week**: Daily totals and punctuation usage patterns.
  - **1 Month / All-Time**: Monthly keystroke volume and speed improvement progression.

---

## 4. Background Service & Lifecycle

* **System Tray Architecture**:
  - Closing the application window hides it to the Windows Taskbar Notification Area (System Tray) using `Shell_NotifyIconW`.
  - Double-clicking the tray icon restores the Dashboard UI.
* **Autostart Configuration**:
  - Optional startup entry via Windows Registry:
    `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\KnowYourClicks`
* **Inter-Process Communication (IPC)**:
  - Named Pipes (`\\.\pipe\knowyourclicks`) for fast and secure local communication between the background service and the GUI.

---

## 5. Windows Tech Stack Recommendation
* **Background Service**: C# (.NET 8 / Win32 Interop) or C++ / Rust using Win32 API (`SetWindowsHookExW`, `SendInput`).
* **GUI Frontend**: Flutter Desktop (Windows target) or C# WPF / WinUI 3.
* **Database**: Local SQLite (via `Microsoft.Data.Sqlite` or standard `sqlite3`).
