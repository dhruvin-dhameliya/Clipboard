import pyperclip
import time
from clipboard.database import add_clipboard_item, get_clipboard_items

class ClipboardMonitor:
    def __init__(self):
        self.prev_content = ""
        self.listeners = []

    def add_listener(self, listener):
        """Register a UI listener to be notified of clipboard changes."""
        self.listeners.append(listener)

    def notify_listeners(self):
        """Notify all registered listeners about clipboard updates."""
        for listener in self.listeners:
            listener.update_items()

    def start_monitoring(self):
        """Continuously monitor clipboard changes."""
        while True:
            content = pyperclip.paste()
            if content != self.prev_content and content.strip():
                self.prev_content = content
                add_clipboard_item(content)
                self.notify_listeners()
            time.sleep(0.3)