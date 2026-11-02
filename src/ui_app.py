"""Native Linux Desktop Window for KnowYourClicks using PyGObject GTK and WebKit.

Provides a true standalone Linux desktop application experience:
- Dedicated native window (not a browser tab)
- Integrated into GNOME/KDE/Fedora desktop shell (WMClass: knowyourclicks)
- Native titlebar, window controls, and application icon
- 100% offline: renders local HTML/CSS/JS with zero external internet dependencies
"""

import os
import sys
import subprocess
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ICON_PNG = BASE_DIR / "icons" / "knowyourclicks.png"
ICON_SVG = BASE_DIR / "icons" / "knowyourclicks.svg"


def launch_native_window(url: str = "http://127.0.0.1:45678/"):
    """Launches the native Linux GTK desktop window embedding the offline dashboard."""
    try:
        import gi
        # Try Gtk 3 + WebKit2 (widely supported on Fedora, Ubuntu, Arch, Debian)
        gi.require_version('Gtk', '3.0')
        gi.require_version('WebKit2', '4.1')
        from gi.repository import Gtk, WebKit2, GdkPixbuf, GLib

        # Set application identity for GNOME Shell and Wayland compositor
        GLib.set_prgname("knowyourclicks")
        GLib.set_application_name("KnowYourClicks")

        win = Gtk.Window(title="KnowYourClicks")
        win.set_default_size(1180, 800)
        win.set_position(Gtk.WindowPosition.CENTER)

        # Set application icon
        icon_file = str(ICON_PNG) if ICON_PNG.exists() else (str(ICON_SVG) if ICON_SVG.exists() else None)
        if icon_file:
            try:
                win.set_icon_from_file(icon_file)
            except Exception:
                pass

        # Create WebKit View
        webview = WebKit2.WebView()
        settings = webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_offline_web_application_cache(True)
        settings.set_enable_developer_extras(False)

        # Scrollable container
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(webview)
        win.add(scrolled)

        # Load local offline dashboard
        webview.load_uri(url)

        # Close UI cleanly on window exit
        win.connect("destroy", Gtk.main_quit)
        win.show_all()
        Gtk.main()
        return True

    except Exception as e:
        print(f"[KnowYourClicks] PyGObject GTK+WebKit unavailable ({e}), trying fallback standalone window...")
        return launch_fallback_window(url)


def launch_fallback_window(url: str = "http://127.0.0.1:45678/"):
    """Fallback if GTK WebKit binding is missing: opens browser in dedicated standalone app-window mode."""
    # Try Chrome/Chromium/Brave standalone app mode
    for browser in ["google-chrome", "google-chrome-stable", "chromium", "brave-browser"]:
        try:
            res = subprocess.run([browser, f"--app={url}"], check=False)
            if res.returncode == 0:
                return True
        except FileNotFoundError:
            continue

    # Try Firefox standalone window
    try:
        res = subprocess.run(["firefox", "--new-window", url], check=False)
        if res.returncode == 0:
            return True
    except FileNotFoundError:
        pass

    # Generic fallback
    import webbrowser
    webbrowser.open(url)
    return True


if __name__ == "__main__":
    url_target = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:45678/"
    launch_native_window(url_target)
