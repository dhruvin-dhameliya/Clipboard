import tkinter as tk
from clipboard.database import get_clipboard_items, clear_clipboard
import pyautogui
import os
import customtkinter as ctk
from PIL import Image
from textwrap import wrap
from functools import partial

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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

        self.popup = ctk.CTkToplevel(self.root)
        self.popup.title("Clipboard")
        self.popup.geometry("400x450+500+200")
        self.popup.overrideredirect(True)
        self.popup.configure(fg_color="#222222")  

        main_header_frame = ctk.CTkFrame(self.popup, fg_color="#292929", corner_radius=10)
        main_header_frame.pack(fill="x", pady=5, padx=10)

        title_label = ctk.CTkLabel(main_header_frame, text="Clipboard", font=("Noto Emoji", 14, "bold"))
        title_label.pack(side="left", padx=15, pady=10)

        close_button = ctk.CTkButton(main_header_frame, text="✖", width=40, command=self.close_popup, fg_color="#444", hover_color="#666")
        close_button.pack(side="right", padx=10, pady=5)

        close_button = ctk.CTkButton(main_header_frame, text="Clear All", width=80, command=self.clear_all, fg_color="#444", hover_color="#666")
        close_button.pack(side="right", padx=10, pady=5)

        main_header_frame.bind("<Button-1>", self.start_move)
        main_header_frame.bind("<B1-Motion>", self.on_move)

        footer = ctk.CTkLabel(self.popup, text="© Dhruvin Dhameliya", fg_color="#222222", text_color="white", font=("Noto Emoji", 10))
        footer.pack(side="bottom", fill="x", pady=0)

        self.popup.bind("<Button-1>", self.check_close_popup)

        self.setup_ui()

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
        self.canvas = ctk.CTkCanvas(self.popup, bg="#222222")
        self.scrollbar = ctk.CTkScrollbar(self.popup, orientation="vertical", command=self.canvas.yview, width=12)  # Thinner scrollbar (adjust the value as needed)
        self.scrollable_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.root.after(100, self.update_items)

    def _bind_mousewheel(self):
        """Bind mouse wheel scrolling to the canvas."""
        if self.root.tk.call('tk', 'windowingsystem') == 'x11':  # Linux (X11)
            self.popup.bind("<Button-4>", self._on_mousewheel_linux)
            self.popup.bind("<Button-5>", self._on_mousewheel_linux)
            self.canvas.bind("<Button-4>", self._on_mousewheel_linux)
            self.canvas.bind("<Button-5>", self._on_mousewheel_linux)
        else:  # Windows and macOS
            self.popup.bind("<MouseWheel>", self._on_mousewheel)
            self.canvas.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling for Windows/macOS."""
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _on_mousewheel_linux(self, event):
        """Handle mouse wheel scrolling for Linux (X11)."""
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def update_items(self):
        """Update the listbox with the latest clipboard items."""
        if not self.popup or not self.popup.winfo_exists():
            return

        if not self.scrollable_frame.winfo_exists():
            return

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.root.after(0, self.fetch_clipboard_items)

    def fetch_clipboard_items(self):
        """Fetch clipboard items and update the UI."""
        self.clipboard_items = get_clipboard_items()[:10]

        self.populate_items()

    def populate_items(self):
        """Populate the UI with clipboard items."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        copy_icon_path = os.path.join(base_dir, "copy_icon.png")
        pil_copy_icon = Image.open(copy_icon_path)

        icon_size = 18

        pil_copy_icon = pil_copy_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        copy_icon = ctk.CTkImage(light_image=pil_copy_icon, size=(icon_size, icon_size))
        self.copy_icon = copy_icon

        popup_width = 400
        popup_height = 450
        card_width = popup_width - 20
        card_height = 80
        button_width_height = 48
        text_width = card_width - button_width_height - 20

        self.popup.geometry(f"{popup_width}x{popup_height}")

        for index, item in enumerate(self.clipboard_items):
            card = ctk.CTkFrame(self.scrollable_frame,
                                width=card_width, 
                                height=card_height, 
                                corner_radius=10,
                                fg_color="#2C2C2C")
            card.pack(padx=5, pady=5, fill="x")
            card.pack_propagate(False)

            if len(self.clipboard_items) > 4:
                self.canvas.configure(yscrollcommand=self.scrollbar.set)
                self.scrollbar.pack(side="right", fill="y")
                self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
                self._bind_mousewheel()
            else:
                self.canvas.configure(yscrollcommand="")
                self.scrollbar.pack_forget()
                self.canvas.unbind_all("<MouseWheel>")
                    
            text_frame = ctk.CTkFrame(card, width=text_width, height=card_height, fg_color="#2C2C2C")
            text_frame.pack(side="left", fill="y", padx=5, pady=5)
            text_frame.pack_propagate(False)

            limited_text = self.limit_text_to_lines(item[1], max_lines=3)

            text_label = ctk.CTkLabel(
                text_frame,
                text=limited_text,
                wraplength=text_width,
                anchor="w",
                justify="left",
                text_color="white",
                font=("Noto Emoji", 12)
            )
            text_label.pack(side="left", fill="both", expand=True, padx=5, pady=5)

            button_frame = ctk.CTkFrame(card, 
                                        width=button_width_height, 
                                        height=button_width_height, 
                                        fg_color="#2C2C2C")
            button_frame.pack(side="right", fill="both", padx=5, pady=5)
            button_frame.pack_propagate(False)

            copy_button = ctk.CTkButton(button_frame, 
                                        image=copy_icon, 
                                        fg_color="#444", 
                                        height=30, 
                                        hover_color="#666", 
                                        command=partial(self.copy_to_clipboard, item[1]), 
                                        anchor="center")
            copy_button.image = copy_icon
            copy_button.pack(side="left", fill="x", expand=True, padx=5, pady=5)

    def limit_text_to_lines(self, text, max_lines=3, width=40):
        """Limit text to fit a specific number of lines with truncation."""
        wrapped_lines = wrap(text, width=width)

        if len(wrapped_lines) < max_lines:
            return "\n".join(wrapped_lines)

        wrapped_lines = wrapped_lines[:max_lines]
        wrapped_lines[-1] = wrapped_lines[-1][:-3] + "..."

        return "\n".join(wrapped_lines)

    def copy_to_clipboard(self, text):
        """Copy text (including emojis) to clipboard and paste it into the active input field."""
        try:
            self.popup.clipboard_clear()
            self.popup.clipboard_append(text)
            self.popup.update()
            pyautogui.hotkey('ctrl', 'v')
            self.close_popup()
        except Exception as e:
                print(f"Error copying to clipboard: {e}")        

    def clear_all(self):
        """Clear all clipboard history."""
        clear_clipboard()
        self.update_items()
        self.canvas.configure(yscrollcommand="")
        self.scrollbar.pack_forget()
        self.canvas.unbind_all("<MouseWheel>")

    def close_popup(self):
        """Close the popup window."""
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.destroy()
            self.popup = None  
            self.scrollable_frame = None

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
        """Handle key press events to open the popup on Win+c."""
        if event.state & 0x0008 and event.keysym.lower() == 'o':
            if self.popup is None or not self.popup.winfo_exists():
                self.show_popup()