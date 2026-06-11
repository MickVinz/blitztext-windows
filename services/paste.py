import time

import keyboard
import win32clipboard
import win32con


class PasteService:
    def paste(self, text: str) -> None:
        self._set_clipboard(text)
        time.sleep(0.08)
        # Ueber die keyboard-Lib senden (echte Scancodes). win32api.keybd_event
        # ohne Scancode wird von Chromium-/Electron-Apps (Browser, viele Chats)
        # ignoriert; keyboard.send funktioniert app-uebergreifend.
        keyboard.send("ctrl+v")

    @staticmethod
    def _set_clipboard(text: str) -> None:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
