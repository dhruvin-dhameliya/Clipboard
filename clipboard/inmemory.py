from collections import deque
from typing import NamedTuple
import time
import zlib

class ClipboardItem(NamedTuple):
    content: str
    timestamp: float

clipboard_data = deque(maxlen=51)
MAX_MEMORY_USAGE = 50 * 1024 * 1024

def add_clipboard_item(content: str):
    """Compresses and adds a text item to the clipboard."""
    try:
        compressed_content = zlib.compress(content.encode("utf-8", errors="ignore"))
        clipboard_data.appendleft(ClipboardItem(compressed_content, time.monotonic()))
        manage_memory()
    except Exception as e:
        print(f"Error compressing clipboard text: {e}")

def get_decompressed_text(item: ClipboardItem) -> str:
    """Decompresses and returns text, or empty string if it's an image."""
    try:
        return zlib.decompress(item.content).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error decompressing text: {e}")
        return ""
    
def get_clipboard_items():
    """Returns all clipboard items."""
    return list(clipboard_data)

def clear_clipboard():
    """Clears all clipboard items."""
    clipboard_data.clear()

def get_clipboard_memory_usage():
    """Returns total memory used by clipboard items."""
    return sum(len(item.content) for item in clipboard_data)

def manage_memory():
    """Removes the oldest clipboard items if memory limit is exceeded."""
    while get_clipboard_memory_usage() > MAX_MEMORY_USAGE and clipboard_data:
        clipboard_data.pop()