import json
import os
import tempfile
import keyring

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
_KEYRING_SERVICE = "blitztext"
_KEYRING_USER = "claude_api_key"

_DEFAULTS = {
    "recording_mode": "push_to_talk",
    "hotkey_transcribe": "ctrl+shift+space",
    "hotkey_improve": "ctrl+shift+alt+space",
    "whisper_model": "tiny",
    "language": "auto",
}


def load() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return _DEFAULTS.copy()
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = {}
    return {**_DEFAULTS, **data}


def save(config: dict) -> None:
    dir_ = os.path.dirname(CONFIG_FILE)
    with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False,
                                     suffix=".tmp", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        tmp_path = f.name
    os.replace(tmp_path, CONFIG_FILE)


def get_api_key() -> str | None:
    return keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER)


def set_api_key(key: str) -> None:
    keyring.set_password(_KEYRING_SERVICE, _KEYRING_USER, key)
