import tkinter as tk
from clipboard.inmemory import ClipboardItem, get_clipboard_items, clear_clipboard, get_decompressed_text
import pyautogui
import os
import customtkinter as ctk
from PIL import Image
from textwrap import wrap
from functools import partial

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

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

    def fade_in(self):
        """Apply fade-in animation to the popup window with less transparency."""
        for i in range(15):
            self.popup.attributes("-alpha", 0.7 + (i / 50))
            self.root.after(20, self.root.update_idletasks)

    def show_popup(self):
        """Show the popup window with an opening animation."""
        if self.popup is not None and self.popup.winfo_exists():
            return

        self.popup = ctk.CTkToplevel(self.root)
        self.popup.wm_attributes("-topmost", True)
        self.popup.attributes("-alpha", 0)

        self.popup.title("Clipboard")
        self.popup.geometry("400x450+500+200")
        self.popup.overrideredirect(True)
        self.popup.configure(fg_color="#1C1C1C", bd=2, highlightthickness=2, highlightbackground="#444")

        main_header_frame = ctk.CTkFrame(self.popup, fg_color="#292929", bg_color="transparent", corner_radius=10, border_width=0)
        main_header_frame.pack(fill="x", pady=5, padx=5)

        title_label = ctk.CTkLabel(main_header_frame, text="Clipboard", font=("Segoe UI", 16, "bold"), text_color="white", fg_color="transparent", anchor="center")
        title_label.pack(side="left", padx=15, pady=10)

        close_button = ctk.CTkButton(main_header_frame, text="✖", width=40, command=self.close_popup, fg_color="#444", hover_color="#666", text_color="white")
        close_button.pack(side="right", padx=(5, 10), pady=5)

        clear_button = ctk.CTkButton(main_header_frame, text="Clear All", width=80, command=self.clear_all, text_color="white", fg_color="transparent", hover_color="#666", border_color="#444", corner_radius=8, border_width=2)
        clear_button.pack(side="right", padx=(5, 5), pady=3)

        main_header_frame.bind("<Button-1>", self.start_move)
        main_header_frame.bind("<B1-Motion>", self.on_move)
        title_label.bind("<Button-1>", self.start_move)
        title_label.bind("<B1-Motion>", self.on_move)

        footer = ctk.CTkLabel(self.popup, text="© Dhruvin Dhameliya", fg_color="#1C1C1C", text_color="white", font=("Segoe UI", 11))
        footer.pack(side="bottom", fill="x", pady=0)

        self.popup.bind("<Button-1>", self.check_close_popup)
        self.popup.bind("<KeyPress-Escape>", lambda e: self.close_popup())

        self.setup_ui()
        self.fade_in()

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
        self.canvas = ctk.CTkCanvas(self.popup, bg="#1C1C1C", highlightthickness=0, bd=0)
        self.scrollbar = ctk.CTkScrollbar(self.popup, orientation="vertical", command=self.canvas.yview, width=12, bg_color="transparent", fg_color="transparent")
        self.scrollable_frame = ctk.CTkFrame(self.canvas, fg_color="transparent", bg_color="transparent", corner_radius=10)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand="")
        self.scrollbar.pack_forget()
        self.canvas.unbind_all("<MouseWheel>")

        self.root.after(100, self.update_items)

    def _bind_mousewheel(self):
        """Bind mouse wheel scrolling to the canvas."""
        if self.root.tk.call('tk', 'windowingsystem') == 'x11':
            self.popup.bind("<Button-4>", self._on_mousewheel_linux)
            self.popup.bind("<Button-5>", self._on_mousewheel_linux)
            self.canvas.bind("<Button-4>", self._on_mousewheel_linux)
            self.canvas.bind("<Button-5>", self._on_mousewheel_linux)
        else:
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

        self.canvas.configure(yscrollcommand="")
        self.scrollbar.pack_forget()
        self.canvas.unbind_all("<MouseWheel>")

        self.popup.geometry(f"{popup_width}x{popup_height}")

        if not self.clipboard_items:
            self.scrollable_frame.grid_rowconfigure(0, weight=1)
            self.scrollable_frame.grid_columnconfigure(0, weight=1)

            empty_box = ctk.CTkFrame(self.scrollable_frame, width=popup_width, height=popup_height, fg_color="transparent", bg_color="transparent")
            empty_box.grid(row=0, column=0, sticky="nsew", pady=(116, 0))
            empty_box.pack_propagate(False)

            empty_box.grid_rowconfigure(0, weight=1)
            empty_box.grid_rowconfigure(1, weight=1)
            empty_box.grid_columnconfigure(0, weight=1)

            empty_title = ctk.CTkLabel(
                empty_box,
                text="Nothing here",
                text_color="white",
                font=("Segoe UI", 16, "bold"),
                anchor="center",
                wraplength=350,
                width=popup_width,
                bg_color="transparent",
                fg_color="transparent"
            )
            empty_title.grid(row=0, column=0, pady=(20,0))
            empty_message = ctk.CTkLabel(
                empty_box,
                text="You'll see your clipboard history here once\nyou've copied something.",
                text_color="white",
                font=("Segoe UI", 14),
                anchor="center",
                wraplength=350,
                fg_color="transparent",
                bg_color="transparent"
            )
            empty_message.grid(row=1, column=0, pady=(5, 20))
            return

        for index, item in enumerate(self.clipboard_items):
            card = ctk.CTkFrame(self.scrollable_frame,
                                width=card_width, 
                                height=card_height, 
                                corner_radius=10,
                                fg_color="#2C2C2C", 
                                bg_color="transparent")
            card.pack(padx=5, pady=5, fill="x")
            card.pack_propagate(False)

            self.bind_hover_events(card, card)

            if len(self.clipboard_items) > 4:
                self.canvas.configure(yscrollcommand=self.scrollbar.set)
                self.scrollbar.pack(side="right", fill="y")
                self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
                self._bind_mousewheel()
            else:
                self.canvas.configure(yscrollcommand="")
                self.scrollbar.pack_forget()
                self.canvas.unbind_all("<MouseWheel>")

            text_frame = ctk.CTkFrame(card, width=text_width, height=card_height, fg_color="#2C2C2C", bg_color="transparent")
            text_frame.pack(side="left", fill="y", padx=5, pady=5)
            text_frame.pack_propagate(False)

            text_data = get_decompressed_text(item)
            limited_text = self.limit_text_to_lines(text_data, max_lines=3)

            text_label = ctk.CTkLabel(
                text_frame,
                text=limited_text,
                wraplength=text_width,
                anchor="w",
                justify="left",
                text_color="white",
                font=("Noto Color Emoji", 14)
            )
            text_label.pack(side="left", fill="both", expand=True, padx=5, pady=5)

            text_label.bind("<Enter>", lambda e, w=card: self.on_hover(w, True))
            text_label.bind("<Leave>", lambda e, w=card: self.on_hover(w, False))

            button_frame = ctk.CTkFrame(card, 
                                        width=button_width_height-5, 
                                        height=button_width_height, 
                                        fg_color="#2C2C2C",
                                        bg_color="transparent")
            button_frame.pack(side="right", fill="both", padx=5, pady=5, anchor="center")
            button_frame.pack_propagate(False)

            copy_button = ctk.CTkButton(button_frame, 
                                        image=copy_icon,
                                        height=30,
                                        text="",                                        
                                        hover_color="#666",
                                        command=partial(self.copy_to_clipboard, item),
                                        fg_color="transparent", 
                                        border_color="#444",
                                        border_width=2,
                                        anchor="center",
                                        bg_color="transparent"
                                        )
            copy_button.image = copy_icon
            copy_button.pack(side="right", fill="x", expand=True, padx=(0, 5), pady=5, anchor="center")
            
            card.bind("<Enter>", lambda e, w=card: self.on_hover(w, True))
            card.bind("<Leave>", lambda e, w=card: self.on_hover(w, False))

            text_frame.bind("<Enter>", lambda e, w=card: self.on_hover(w, True))
            text_frame.bind("<Leave>", lambda e, w=card: self.on_hover(w, False))

            text_label.bind("<Enter>", lambda e, w=card: self.on_hover(w, True))
            text_label.bind("<Leave>", lambda e, w=card: self.on_hover(w, False))

            button_frame.bind("<Enter>", lambda e, w=card: self.on_hover(w, True))
            button_frame.bind("<Leave>", lambda e, w=card: self.on_hover(w, False))

    def bind_hover_events(self, widget, card):
        """Bind hover events to a widget and its children."""
        widget.bind("<Enter>", lambda e, w=card: self.on_hover(w, True))
        widget.bind("<Leave>", lambda e, w=card: self.on_hover(w, False))
        for child in widget.winfo_children():
            self.bind_hover_events(child, card)

    def on_hover(self, card, enter):
        """Handle hover enter and leave events."""
        color = "#3C3C3C" if enter else "#2C2C2C"
        border_color = "#666" if enter else "#2C2C2C"
        card.configure(fg_color=color, border_color=border_color, border_width=2 if enter else 0)
        for child in card.winfo_children():
            child.configure(fg_color=color)

    def limit_text_to_lines(self, text, max_lines=3, width=40):
        """Limit text to fit a specific number of lines with truncation."""
        wrapped_lines = wrap(text, width=width)

        if len(wrapped_lines) < max_lines:
            return "\n".join(wrapped_lines)

        wrapped_lines = wrapped_lines[:max_lines]
        wrapped_lines[-1] = wrapped_lines[-1][:-3] + "..."

        return "\n".join(wrapped_lines)

    def copy_to_clipboard(self, clipboard_item: ClipboardItem):
        """Copy text (including emojis) to clipboard and paste it into the active input field."""
        try:
            self.popup.clipboard_clear()
            txt = get_decompressed_text(clipboard_item)
            self.popup.clipboard_append(txt)
            self.popup.update()
            pyautogui.hotkey('ctrl', 'v')
            self.close_popup()

        except Exception as e:
            print(f"Error copying to clipboard: {e}")

    def clear_all(self):
        """Clear all clipboard history."""
        if not self.clipboard_items:
            return
        clear_clipboard()
        self.clipboard_items = []
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