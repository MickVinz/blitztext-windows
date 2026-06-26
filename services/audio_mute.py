import comtypes
from pycaw.pycaw import AudioUtilities


class SystemMute:
    """Schaltet die System-Audioausgabe (Lautsprecher) waehrend der Aufnahme
    stumm, damit Hintergrund-Ton (Musik, Videos) nicht stoert. Das Mikrofon
    (Eingang) bleibt davon unberuehrt. Ein zuvor schon gesetzter Mute-Zustand
    wird respektiert.

    mute() und unmute() werden aus verschiedenen Threads aufgerufen (Hotkey-
    Thread bzw. Verarbeitungs-Thread). pycaw/comtypes braucht COM pro Thread
    initialisiert, sonst schlaegt der Aufruf still fehl und der Ton bliebe
    stumm. Darum vor jedem Zugriff CoInitialize().
    """

    def __init__(self) -> None:
        self._was_muted: int | None = None

    @staticmethod
    def _endpoint():
        comtypes.CoInitialize()
        return AudioUtilities.GetSpeakers().EndpointVolume

    def mute(self) -> None:
        try:
            vol = self._endpoint()
            self._was_muted = vol.GetMute()
            vol.SetMute(1, None)
        except Exception:
            self._was_muted = None

    def unmute(self) -> None:
        # Nur entmuten, wenn die Ausgabe vor der Aufnahme NICHT stumm war.
        try:
            if self._was_muted == 0:
                self._endpoint().SetMute(0, None)
        except Exception:
            pass
        finally:
            self._was_muted = None
