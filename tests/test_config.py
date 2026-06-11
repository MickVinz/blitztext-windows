import json
import importlib
import pytest
from unittest.mock import MagicMock


def test_load_returns_defaults_when_no_file(tmp_path, monkeypatch):
    import config
    importlib.reload(config)
    monkeypatch.setattr("config.CONFIG_FILE", str(tmp_path / "config.json"))
    result = config.load()
    assert result["recording_mode"] == "push_to_talk"
    assert result["hotkey_transcribe"] == "ctrl+shift+space"
    assert result["hotkey_improve"] == "ctrl+shift+alt+space"
    assert result["whisper_model"] == "tiny"
    assert result["language"] == "auto"


def test_load_merges_with_defaults(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"whisper_model": "base", "language": "de"}))
    import config
    importlib.reload(config)
    monkeypatch.setattr("config.CONFIG_FILE", str(cfg_file))
    result = config.load()
    assert result["whisper_model"] == "base"
    assert result["language"] == "de"
    assert result["recording_mode"] == "push_to_talk"


def test_save_writes_json(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    import config
    importlib.reload(config)
    monkeypatch.setattr("config.CONFIG_FILE", str(cfg_file))
    config.save({"recording_mode": "toggle", "whisper_model": "tiny",
                 "hotkey_transcribe": "ctrl+shift+space",
                 "hotkey_improve": "ctrl+shift+alt+space", "language": "de"})
    data = json.loads(cfg_file.read_text())
    assert data["recording_mode"] == "toggle"


def test_get_api_key_returns_none_when_not_set(monkeypatch):
    import config
    importlib.reload(config)
    mock_kr = MagicMock()
    mock_kr.get_password.return_value = None
    monkeypatch.setattr("config.keyring", mock_kr)
    assert config.get_api_key() is None


def test_set_and_get_api_key(monkeypatch):
    stored = {}
    mock_kr = MagicMock()
    mock_kr.get_password.side_effect = lambda s, u: stored.get((s, u))
    mock_kr.set_password.side_effect = lambda s, u, v: stored.update({(s, u): v})
    import config
    importlib.reload(config)
    monkeypatch.setattr("config.keyring", mock_kr)
    config.set_api_key("sk-test")
    assert config.get_api_key() == "sk-test"
