import tkinter as tk
from tkinter import ttk
from clipboard.database import get_clipboard_items, clear_clipboard
import pyperclip
import pyautogui

class ClipboardManagerUI:
    def __init__(self, clipboard_monitor, action_queue):
        self.clipboard_monitor = clipboard_monitor
        self.action_queue = action_queue
        self.popup = None
        self.clipboard_items = []

        self.root = tk.Tk()
        self.root.withdraw()

        self.clipboard_monitor.add_listener(self)

        self.process_queue()

        self.bind_hotkey()

    def process_queue(self):
        """Process actions from the queue to update the GUI."""
        try:
            while not self.action_queue.empty():
                action = self.action_queue.get_nowait()
                if action == "TOGGLE_POPUP":
                    self._toggle_popup()
        except Exception as e:
            print(f"Error processing queue: {e}")
        finally:
            self.root.after(100, self.process_queue)

    def toggle_popup(self):
        """Put a toggle popup action into the queue."""
        self.action_queue.put("TOGGLE_POPUP")

    def _toggle_popup(self):
        """Toggle the clipboard manager popup window."""
        if self.popup is None or not self.popup.winfo_exists():
            self.show_popup()
        else:
            self.close_popup()

    def show_popup(self):
        """Show the popup window."""
        if self.popup is not None and self.popup.winfo_exists():
            return

        self.popup = tk.Toplevel(self.root)
        self.popup.title("Clipboard Manager")
        self.popup.geometry("450x500+500+300")
        self.popup.overrideredirect(True)
        self.popup.configure(bg="#222222")

        header_frame = tk.Frame(self.popup, bg="#222222", height=75)
        header_frame.pack(side="top", fill="x")

        title_label = tk.Label(
            header_frame,
            text="Clipboard",
            fg="white",
            bg="#222222",
            font=("Arial", 12, "bold")
        )
        title_label.pack(side="left", padx=15, pady=15)

        clear_button = ttk.Button(header_frame, text="Clear All", command=self.clear_all)
        clear_button.pack(side="right", padx=15, pady=15)

        header_frame.bind("<Button-1>", self.start_move)
        header_frame.bind("<B1-Motion>", self.on_move)

        self.popup.bind("<Button-1>", self.check_close_popup)

        self.setup_ui()

        self.popup.lift()
        self.popup.focus_force()
        self.popup.grab_set()


    def start_move(self, event):
        """Start moving the popup window."""
        self._start_x = event.x
        self._start_y = event.y


    def on_move(self, event):
        """Handle the movement of the popup window."""
        x = self.popup.winfo_x() + (event.x - self._start_x)
        y = self.popup.winfo_y() + (event.y - self._start_y)
        self.popup.geometry(f"+{x}+{y}")
        
        
    def setup_ui(self):
        """Set up the UI elements in the popup."""
        self.canvas = tk.Canvas(self.popup)
        self.scrollbar = ttk.Scrollbar(self.popup, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self._bind_mousewheel()

        self.update_items()

    def _bind_mousewheel(self):
        """Bind mouse wheel scrolling to the canvas."""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")


    def update_items(self):
        """Update the listbox with the latest clipboard items."""
        if self.popup is None or not self.popup.winfo_exists():
            return

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.clipboard_items = get_clipboard_items()

        popup_width = 450
        popup_height = 500
        card_width = popup_width - 10
        card_height = 100
        button_width = 40
        text_width = card_width - button_width - 20

        self.popup.geometry(f"{popup_width}x{popup_height}")

        copy_icon = tk.PhotoImage(file="copy_icon.png")
        copy_icon = copy_icon.subsample(18, 18)

        for item in self.clipboard_items:
            card = tk.Frame(self.scrollable_frame, bg="#2C2C2C", relief="groove", borderwidth=0, width=card_width, height=card_height)
            card.pack(padx=5, pady=5)
            card.pack_propagate(False)

            text_frame = tk.Frame(card, bg="#2C2C2C", width=text_width, height=card_height)
            text_frame.pack(side="left", fill="y", padx=5, pady=5)
            text_frame.pack_propagate(False)

            limited_text = self.limit_text_to_lines(item[1], max_lines=3, width=text_width)

            text_label = tk.Label(
                text_frame,
                text=limited_text,
                wraplength=text_width,
                anchor="w",
                justify="left",
                bg="#2C2C2C",
                fg="white",
                font=("Arial", 11)
            )
            text_label.pack(fill="both", expand=True, padx=5, pady=5)

            button_frame = tk.Frame(card, bg="#2C2C2C", width=button_width, height=card_height)
            button_frame.pack(side="right", fill="y", padx=5)
            button_frame.pack_propagate(False)

            copy_button = ttk.Button(button_frame, image=copy_icon, command=lambda text=item[1]: self.copy_to_clipboard(text, card))
            copy_button.image = copy_icon
            copy_button.pack(expand=True, pady=10)

    def limit_text_to_lines(self, text, max_lines=3, width=400):
        """Limit text to fit a specific number of lines with truncation."""
        from textwrap import wrap

        wrapped_lines = wrap(text, width=width // 10)
        wrapped_lines = wrapped_lines[:max_lines]

        if len(wrapped_lines) == max_lines and len(text) > sum(len(line) for line in wrapped_lines):
            wrapped_lines[-1] = wrapped_lines[-1][:-3] + "..."

        return "\n".join(wrapped_lines)


    def copy_to_clipboard(self, text, card):
        """Copy the given text to the clipboard and paste it into the active input field."""
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        self.close_popup()

    def clear_all(self):
        """Clear all clipboard history."""
        clear_clipboard()
        self.update_items()

    def close_popup(self):
        """Close the popup window."""
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.destroy()
            self.popup = None

    def check_close_popup(self, event):
        """Check if the click is outside the popup and close it if necessary."""
        if self.popup and self.popup.winfo_exists():
            x_root, y_root = event.x_root, event.y_root
            
            if not (self.popup.winfo_x() <= x_root <= self.popup.winfo_x() + self.popup.winfo_width() and
                    self.popup.winfo_y() <= y_root <= self.popup.winfo_y() + self.popup.winfo_height()):
                self.close_popup()

    def bind_hotkey(self):
        """Bind the hotkey to open the clipboard manager."""
        self.root.bind("<KeyPress>", self.key_press_handler)

    def key_press_handler(self, event):
        """Handle key press events to open the popup on Win+O."""
        if event.state & 0x0008 and event.keysym.lower() == 'o':
            if self.popup is None or not self.popup.winfo_exists():
                self.show_popup()