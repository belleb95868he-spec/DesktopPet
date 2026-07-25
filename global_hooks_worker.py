import time
import os
import sys
try:
    from pynput import mouse
    from pynput import keyboard
except Exception:
    mouse = None
    keyboard = None


def run(conn):
    """Run in a separate process: listen for global mouse/keyboard and send events back.

    Protocol: send tuples (event_type, payload)
    event_type: 'click' -> payload (x, y)
                'key'   -> payload None
    """
    if mouse is None or keyboard is None:
        conn.send(("error", "pynput-unavailable"))
        return

    def on_click(x, y, button, pressed):
        if pressed:
            try:
                conn.send(("click", (x, y)))
            except Exception:
                pass

    def on_press(key):
        try:
            conn.send(("key", None))
        except Exception:
            pass

    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)

    mouse_listener.start()
    keyboard_listener.start()

    try:
        # Keep process alive while listeners run
        while True:
            time.sleep(1)
            if conn.closed:
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            mouse_listener.stop()
        except Exception:
            pass
        try:
            keyboard_listener.stop()
        except Exception:
            pass
