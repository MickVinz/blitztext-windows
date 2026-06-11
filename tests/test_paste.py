import sys
from unittest.mock import MagicMock, patch


def _make_mocks():
    mock_cb = MagicMock()
    mock_con = MagicMock()
    mock_con.CF_UNICODETEXT = 13
    mock_con.VK_CONTROL = 0x11
    mock_con.KEYEVENTF_KEYUP = 0x0002
    mock_api = MagicMock()
    mock_time = MagicMock()
    return mock_cb, mock_con, mock_api, mock_time


def test_paste_sets_clipboard():
    mock_cb, mock_con, mock_api, mock_time = _make_mocks()
    with patch.dict(sys.modules, {"win32clipboard": mock_cb, "win32con": mock_con,
                                   "win32api": mock_api, "time": mock_time}):
        import importlib, services.paste as m; importlib.reload(m)
        m.PasteService().paste("Hallo Welt")
    mock_cb.OpenClipboard.assert_called_once()
    mock_cb.SetClipboardText.assert_called_once_with("Hallo Welt", 13)
    mock_cb.CloseClipboard.assert_called_once()


def test_paste_sends_four_key_events():
    mock_cb, mock_con, mock_api, mock_time = _make_mocks()
    with patch.dict(sys.modules, {"win32clipboard": mock_cb, "win32con": mock_con,
                                   "win32api": mock_api, "time": mock_time}):
        import importlib, services.paste as m; importlib.reload(m)
        m.PasteService().paste("Test")
    assert mock_api.keybd_event.call_count == 4
