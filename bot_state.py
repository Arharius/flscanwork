"""
Shared mutable state between main.py and dashboard.py.
Both modules import this to read/write the same objects in the same process.
"""
import threading
from datetime import datetime

_lock = threading.Lock()

# Pause flag — mirrors _BOT_PAUSED in main.py; dashboard writes here, main_cycle reads
paused: bool = False

# Trigger for immediate search
search_now: bool = False

# Kwork session cookie health
_kwork_cookie: dict = {
    "valid": None,          # None = not yet checked, True = OK, False = expired/invalid
    "checked_at": "",       # timestamp of last check
    "error": "",            # error message if invalid
    "set_at": "",           # when cookie was first loaded from env
    "expires_at": "",       # parsed expiry date string (if found in cookie)
    "days_remaining": None, # int days until expiry, or None if unknown
}

# FL.ru session cookie health
_flru_cookie: dict = {
    "valid": None,
    "checked_at": "",
    "error": "",
    "set_at": "",
    "expires_at": "",
    "days_remaining": None,
}


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


def set_kwork_cookie_valid(valid: bool, error: str = "", expires_at: str = "", days_remaining=None):
    with _lock:
        _kwork_cookie["valid"] = valid
        _kwork_cookie["checked_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        _kwork_cookie["error"] = error
        if not _kwork_cookie["set_at"]:
            _kwork_cookie["set_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        if expires_at:
            _kwork_cookie["expires_at"] = expires_at
        if days_remaining is not None:
            _kwork_cookie["days_remaining"] = days_remaining


def get_kwork_cookie_status() -> dict:
    with _lock:
        return dict(_kwork_cookie)


def set_kwork_cookie_expires(expires_at: str, days_remaining: int):
    """Update only the expiry fields (called at startup after parsing cookie)."""
    with _lock:
        _kwork_cookie["expires_at"] = expires_at
        _kwork_cookie["days_remaining"] = days_remaining
        if not _kwork_cookie["set_at"]:
            _kwork_cookie["set_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def set_flru_cookie_valid(valid: bool, error: str = "", expires_at: str = "", days_remaining=None):
    with _lock:
        _flru_cookie["valid"] = valid
        _flru_cookie["checked_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        _flru_cookie["error"] = error
        if not _flru_cookie["set_at"]:
            _flru_cookie["set_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        if expires_at:
            _flru_cookie["expires_at"] = expires_at
        if days_remaining is not None:
            _flru_cookie["days_remaining"] = days_remaining


def get_flru_cookie_status() -> dict:
    with _lock:
        return dict(_flru_cookie)
