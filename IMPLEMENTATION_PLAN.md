# Linux Implementation Plan: KnowYourClicks

## 1. System Overview & Platform Architecture

On Linux (specifically modern distributions like Fedora, Ubuntu, Arch using Wayland or X11), input monitoring and background execution have strict permission models. To ensure privacy compliance, continuous background execution, and non-cloud local persistence, the Linux architecture is split into a **System Daemon** and a **Client GUI**.

```mermaid
flowchart TD
    subgraph LinuxHost ["Linux System (Wayland / X11)"]
        KernelInput["/dev/input/event* (evdev)"] -->|Raw Kernel Events| PrivacyFilter["Hardware Privacy Filter"]
        
        subgraph BackgroundDaemon ["Background Daemon (Systemd / Tray)"]
            PrivacyFilter -->|Allowed: Space, Punctuation, BS, Del| EventProcessor["Event Processor & Word Counter"]
            PrivacyFilter -->|Dropped Immediately: Letters, Numbers| Trash["Discarded (Zero Memory Log)"]
            
            EventProcessor --> LocalDB[("Local SQLite (~/.local/share/knowyourclicks/)")]
            EventProcessor --> SpeedEngine["Background Speed Timer (30/60/90/120s)"]
            
            UInput["/dev/uinput"] <---|Simulate Backspace & Expansion| TextExpander["Text Expansion Worker"]
        end
        
        subgraph GUIApp ["GUI Application (GTK / Flutter Desktop / Qt)"]
            DashboardUI["Analytics Dashboard (1h, 1d, 1w, 1mo)"]
            TypingScreen["Typing Screen & Shortcut Test"]
            SpeedTestUI["In-App Given Text Speed Test"]
        end
        
        BackgroundDaemon <-->|Unix Domain Socket (~/run/knowyourclicks.sock)| GUIApp
    end
```

---

## 2. Privacy-First Kernel Whitelist Filter

To satisfy the strict privacy requirement:
> *"sense only spacebar, punctuation marks, and backspace and delete keys. others shouldn't be sensed by the app for privacy reasons."*

The Linux listener intercepts events at the `evdev` interface (`/dev/input/event*`) and uses an explicit kernel scancode whitelist. Any key not on this list is dropped at the earliest hardware interrupt evaluation stage before entering any buffer.

### Whitelisted Linux Evdev Keycodes
| Category | Allowed Scancodes (`linux/input-event-codes.h`) |
| :--- | :--- |
| **Space** | `KEY_SPACE` (57) |
| **Editing** | `KEY_BACKSPACE` (14), `KEY_DELETE` (111) |
| **Punctuation** | `KEY_DOT` (52), `KEY_COMMA` (51), `KEY_SLASH` (53), `KEY_SEMICOLON` (39), `KEY_APOSTROPHE` (40), `KEY_GRAVE` (41), `KEY_MINUS` (12), `KEY_EQUAL` (13), `KEY_LEFTBRACE` (26), `KEY_RIGHTBRACE` (27), `KEY_BACKSLASH` (43) |
| **Alphanumerics (A-Z, 0-9)** | **BLOCKED & DROPPED** — Never parsed, logged, or buffered |

### Permissions Configuration
To allow the daemon to access `/dev/input` without requiring root privileges:
* Create a udev rule `/etc/udev/rules.d/99-knowyourclicks.rules`:
  ```bash
  KERNEL=="uinput", GROUP="input", MODE="0660"
  ```
* Add the user to the `input` group:
  ```bash
  sudo usermod -aG input $USER
  ```

---

## 3. Features & Logic

### A. Text Expander & Shortcut Option (on Space Key)
* **Typing Screen Integration**: In the app's typing screen, user input captures word tokens.
* **Trigger Mechanism**:
  1. The typing screen tracks words entered by the user.
  2. The moment the **Spacebar** (`KEY_SPACE`) is received, the word immediately preceding the space is evaluated against the `shortcuts` SQLite table.
  3. If matched (e.g., `idk`), the text area automatically replaces `idk ` with `i dont know `.
* **System-Wide Expansion (Optional uinput Mode)**:
  - When enabled, `/dev/uinput` emits $(N \times \text{Backspace})$ keystrokes followed by the replacement string character scancodes.

### B. Timed Typing Speed Tracker
Only activates when triggered by the user.
* **Durations**: `30s`, `60s`, `90s`, `120s`.
* **Option 1: Try with Given Text (In-App)**
  - Presents randomized paragraphs or prompts in the typing screen.
  - Measures Characters Per Minute (CPM), Words Per Minute (WPM), and Accuracy (%).
  - Evaluates error rates based on backspace usage and word match accuracy.
* **Option 2: Measure in the Background**
  - Triggered via System Tray menu or global hotkey.
  - Since letters are masked for privacy, speed is calculated using the **Spacebar & Punctuation Cadence**:
    $$\text{Words Counted} = \text{Count}(\text{KEY\_SPACE}) + \text{Count}(\text{Sentence Delimiters})$$
    $$\text{WPM} = \frac{\text{Words Counted}}{\text{Elapsed Time (minutes)}}$$
  - Sends a desktop notification via `libnotify` (`notify-send`) upon completion with the final WPM score.

### C. Local Analytics & Statistics (Zero Cloud)
* **Storage Location**: `~/.local/share/knowyourclicks/stats.db` (following XDG Base Directory specification).
* **Aggregate Reporting Windows**:
  - **1 Hour**: Minute-by-minute frequency of Space, Backspaces, and Punctuation marks.
  - **1 Day**: Hourly breakdown showing peak typing intensity periods.
  - **1 Week**: Daily distribution and edit-ratio (Backspaces/Deletes vs. Spaces).
  - **1 Month & All-Time**: Monthly volume, most used punctuation marks, and typing speed trends.

---

## 4. Background Service & Lifecycle

* **Systemd User Service**: Runs continuously in the background even if the GUI is closed.
  - Service file: `~/.config/systemd/user/knowyourclicks.service`
  ```ini
  [Unit]
  Description=KnowYourClicks Background Input Daemon
  After=graphical-session.target

  [Service]
  ExecStart=/usr/local/bin/knowyourclicks-daemon
  Restart=on-failure

  [Install]
  WantedBy=default.target
  ```
* **System Tray Indicator**: Uses Ayatana AppIndicator (`libayatana-appindicator`) to provide a tray icon with Quick Start Timers (30s, 60s, 90s, 120s) and an "Open Dashboard" button.

---

## 5. Linux Tech Stack Recommendation
* **Daemon**: Python (`evdev`, `python-uinput`) or C / Rust (`evdev-rs`) for zero-overhead background processing.
* **IPC**: Unix Domain Socket (`/tmp/knowyourclicks-$UID.sock`).
* **GUI Frontend**: Flutter Desktop (Linux GTK bundle) or PySide6 / PyQt6.
* **Database**: Local SQLite 3 embedded.
