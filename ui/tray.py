import pystray
from assets.icons import ICONS


class TrayApp:
    def __init__(self, on_settings, on_quit) -> None:
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._status = "Wird geladen..."
        self._icon: pystray.Icon | None = None

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(f"● {self._status}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Einstellungen...", lambda icon, item: self._on_settings()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", lambda icon, item: self._quit()),
        )

    def set_state(self, state: str, message: str = "") -> None:
        if message:
            self._status = message
        if self._icon:
            self._icon.icon = ICONS.get(state, ICONS["ready"])
            self._icon.menu = self._build_menu()

    def _quit(self) -> None:
        if self._icon:
            self._icon.stop()
        self._on_quit()

    def run(self) -> None:
        self._icon = pystray.Icon(
            "blitztext",
            ICONS["processing"],
            "Blitztext",
            menu=self._build_menu(),
        )
        self._icon.run()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
