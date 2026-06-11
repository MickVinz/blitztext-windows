# Blitztext Windows — Design Spec
_2026-06-11_

## Überblick

Python-Port der macOS-App blitztext-app für Windows. Push-to-Talk-Diktier-Tool mit System-Tray, lokaler Spracherkennung und optionaler KI-Textverbesserung.

## Projektstruktur

```
blitztext/
  main.py
  config.py
  services/
    audio.py
    transcription.py
    llm.py
    hotkey.py
    paste.py
  ui/
    tray.py
    settings.py
  assets/
    icon_ready.png
    icon_recording.png
    icon_processing.png
    icon_error.png
  requirements.txt
```

## Dependencies

| Package | Zweck |
|---|---|
| faster-whisper | Lokale STT (CUDA, GTX 750 Ti) |
| anthropic | Claude API (Haiku 4.5) |
| sounddevice | Mikrofon-Aufnahme |
| keyboard | Globale Hotkeys |
| pystray | System-Tray Icon + Menü |
| pywin32 | Auto-Paste + Clipboard |
| pillow | Tray-Icon rendern |
| keyring | API-Key im Windows Credential Manager |

## Workflows

### Blitztext (Transkription)
1. Hotkey gedrückt → `AudioService` startet Aufnahme
2. Hotkey losgelassen (PTT) oder nochmal gedrückt (Toggle) → Aufnahme stoppt, WAV tempfile
3. `TranscriptionService.transcribe(wav)` → Text via faster-whisper (tiny-Modell, CUDA)
4. `PasteService.paste(text)` → Clipboard → SendInput in aktives Fenster

### Blitztext+ (Textverbesserung)
1–3. Identisch mit Blitztext
4. `LLMService.improve(text)` → Claude API (claude-haiku-4-5): Rohtext → sauberer Text
5. `PasteService.paste(improved_text)`

## Aufnahme-Modi

| Modus | Verhalten |
|---|---|
| Push-to-Talk | Hotkey halten = Aufnahme, loslassen = fertig |
| Toggle | 1× drücken = Start, nochmal = Stop |

Umschaltbar in Settings, gilt für beide Workflows.

## Einstellungen

Gespeichert in `config.json` (neben `main.py`):

```json
{
  "recording_mode": "push_to_talk",
  "hotkey_transcribe": "ctrl+shift+space",
  "hotkey_improve": "ctrl+shift+alt+space",
  "whisper_model": "tiny",
  "language": "auto"
}
```

Claude API-Key: Windows Credential Manager via `keyring` — kein Klartext.

Settings-Fenster (tkinter) öffnet per Tray → Einstellungen. Hotkeys sofort wirksam nach Speichern, kein Neustart nötig.

## Tray-Icon

| Zustand | Farbe |
|---|---|
| Bereit | Grün |
| Aufnahme | Rot (blinkt) |
| Verarbeitung (STT/LLM) | Gelb |
| Fehler | Grau |

Rechtsklick-Menü:
- Status-Zeile (read-only)
- Einstellungen...
- Modell neu laden
- Beenden

Keine Popup-Fenster während Nutzung. Alles läuft im Hintergrund.

## Modell

- Standard: `tiny` (schnell, ~1-2s für kurze Clips, 2GB VRAM reicht)
- Optional: `base` oder `small` in Settings wählbar
- Wird beim Start einmalig geladen (kein Reload pro Aufnahme)

## Fehlerbehandlung

- Kein Mikrofon gefunden → Tray-Icon grau, Fehlermeldung im Menü
- Claude API-Key fehlt → Blitztext+ deaktiviert, Hinweis in Settings
- Whisper-Modell nicht geladen → Fehlermeldung, Retry-Option im Tray
- Paste fehlgeschlagen → Text bleibt in Clipboard, kurze Toast-Benachrichtigung

## Nicht im Scope

- Blitztext $%&! (Dampf ablassen)
- Blitztext :) (Emoji-Modus)
- Lokale Modell-Downloads per UI (Modell manuell installieren)
- Multi-Monitor / Multi-Sprache UI
