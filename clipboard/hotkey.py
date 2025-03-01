from pynput import keyboard
import threading

class HotkeyListener:
    def __init__(self, on_activate_callback):
        self.on_activate_callback = on_activate_callback
        self.is_win_pressed = False
    def start(self):
        def on_press(key):
            try:
                if key == keyboard.Key.cmd:
                    self.is_win_pressed = True
                elif self.is_win_pressed and key.char == 'o':
                    threading.Thread(target=self.on_activate_callback, daemon=True).start()
            except AttributeError:
                pass

        def on_release(key):
            if key == keyboard.Key.cmd:
                self.is_win_pressed = False

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()