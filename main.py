import os
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
from queue import Queue
import threading
from clipboard.ui import ClipboardManagerUI
from clipboard.manager import ClipboardMonitor
from clipboard.hotkey import HotkeyListener
from clipboard.database import init_db

def main():
    init_db()

    action_queue = Queue()

    clipboard_monitor = ClipboardMonitor()

    monitor_thread = threading.Thread(target=clipboard_monitor.start_monitoring, daemon=True)
    monitor_thread.start()

    clipboard_ui = ClipboardManagerUI(clipboard_monitor, action_queue)

    clipboard_ui.bind_hotkey()

    hotkey_listener = HotkeyListener(on_activate_callback=clipboard_ui.toggle_popup)
    hotkey_thread = threading.Thread(target=hotkey_listener.start, daemon=True)
    hotkey_thread.start()

    clipboard_ui.root.mainloop()

if __name__ == "__main__":
    main()