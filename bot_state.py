"""
Shared mutable state between main.py and dashboard.py.
Both modules import this to read/write the same objects in the same process.
"""
import threading

_lock = threading.Lock()

# Pause flag — mirrors _BOT_PAUSED in main.py; dashboard writes here, main_cycle reads
paused: bool = False

# Trigger for immediate search
search_now: bool = False


def set_paused(value: bool):
    global paused
    with _lock:
        paused = value


def is_paused() -> bool:
    with _lock:
        return paused


def trigger_search():
    global search_now
    with _lock:
        search_now = True


def consume_search_trigger() -> bool:
    global search_now
    with _lock:
        if search_now:
            search_now = False
            return True
        return False
