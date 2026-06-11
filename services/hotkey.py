import keyboard


class HotkeyService:
    def __init__(self) -> None:
        self._hooks: list = []

    def setup_ptt(self, hotkey: str, on_start, on_stop) -> None:
        """Push-to-talk: on_start when held, on_stop when released."""
        keys = [k.strip().lower() for k in hotkey.split("+")]
        trigger = keys[-1]
        modifiers = keys[:-1]
        active = [False]

        def on_event(e):
            if e.name != trigger:
                return
            if e.event_type == keyboard.KEY_DOWN:
                if not active[0] and all(keyboard.is_pressed(m) for m in modifiers):
                    active[0] = True
                    on_start()
            elif e.event_type == keyboard.KEY_UP:
                if active[0]:
                    active[0] = False
                    on_stop()

        self._hooks.append(keyboard.hook(on_event))

    def setup_toggle(self, hotkey: str, on_toggle) -> None:
        """Toggle: on_toggle called each time hotkey fires."""
        self._hooks.append(keyboard.add_hotkey(hotkey, on_toggle))

    def unregister_all(self) -> None:
        for h in self._hooks:
            try:
                keyboard.unhook(h)
            except Exception:
                pass
        self._hooks.clear()
