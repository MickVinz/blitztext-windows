import tkinter as tk
from tkinter import ttk
import config as cfg


class SettingsWindow:
    def open(self, current_config: dict, on_save) -> None:
        root = tk.Tk()
        root.title("Blitztext — Einstellungen")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        pad = {"padx": 10, "pady": 5}

        tk.Label(root, text="Aufnahme-Modus:").grid(row=0, column=0, sticky="w", **pad)
        mode_var = tk.StringVar(value=current_config["recording_mode"])
        ttk.Combobox(root, textvariable=mode_var,
                     values=["push_to_talk", "toggle"],
                     state="readonly", width=24).grid(row=0, column=1, **pad)

        tk.Label(root, text="Hotkey Transkription:").grid(row=1, column=0, sticky="w", **pad)
        hk_t = tk.StringVar(value=current_config["hotkey_transcribe"])
        tk.Entry(root, textvariable=hk_t, width=27).grid(row=1, column=1, **pad)

        tk.Label(root, text="Hotkey Verbesserung:").grid(row=2, column=0, sticky="w", **pad)
        hk_i = tk.StringVar(value=current_config["hotkey_improve"])
        tk.Entry(root, textvariable=hk_i, width=27).grid(row=2, column=1, **pad)

        tk.Label(root, text="Whisper-Modell:").grid(row=3, column=0, sticky="w", **pad)
        model_var = tk.StringVar(value=current_config["whisper_model"])
        ttk.Combobox(root, textvariable=model_var,
                     values=["tiny", "base", "small"],
                     state="readonly", width=24).grid(row=3, column=1, **pad)

        tk.Label(root, text="Sprache:").grid(row=4, column=0, sticky="w", **pad)
        lang_var = tk.StringVar(value=current_config["language"])
        ttk.Combobox(root, textvariable=lang_var,
                     values=["auto", "de", "en"],
                     state="readonly", width=24).grid(row=4, column=1, **pad)

        tk.Label(root, text="Claude API-Key:").grid(row=5, column=0, sticky="w", **pad)
        api_var = tk.StringVar(value=cfg.get_api_key() or "")
        tk.Entry(root, textvariable=api_var, show="*", width=27).grid(row=5, column=1, **pad)

        def save():
            new_cfg = {
                "recording_mode": mode_var.get(),
                "hotkey_transcribe": hk_t.get(),
                "hotkey_improve": hk_i.get(),
                "whisper_model": model_var.get(),
                "language": lang_var.get(),
            }
            cfg.save(new_cfg)
            key = api_var.get().strip()
            if key:
                cfg.set_api_key(key)
            on_save(new_cfg)
            root.destroy()

        tk.Button(root, text="Speichern", command=save, width=14).grid(
            row=6, column=0, columnspan=2, pady=12)
        root.mainloop()


if __name__ == "__main__":
    # Standalone-Prozess: vom Tray per subprocess gestartet, damit tkinter
    # im eigenen Hauptthread läuft (nicht thread-safe in pystray-Daemon-Thread).
    SettingsWindow().open(cfg.load(), lambda c: None)
