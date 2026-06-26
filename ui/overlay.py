import sys
import tkinter as tk

# Standalone-Overlay: vom Tray per subprocess gestartet, damit tkinter im
# eigenen Hauptthread laeuft. Zeigt ein randloses, immer-im-Vordergrund
# Banner. "recording"/"processing" laufen bis der Elternprozess sie
# terminiert; Flash-Modi (z.B. "empty") schliessen sich selbst nach kurzer
# Zeit.

# mode -> (hintergrundfarbe, text, auto_close_ms | None)
_MODES = {
    "recording":  ("#F44336", "● Aufnahme läuft",     None),
    "processing": ("#FFC107", "● Wird verarbeitet…",   None),
    "empty":      ("#9E9E9E", "● Nichts erkannt",     1600),
    "notready":   ("#FFC107", "● Modell lädt noch…",  1800),
}


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "recording"
    bg, text, auto_close = _MODES.get(mode, _MODES["recording"])

    root = tk.Tk()
    root.overrideredirect(True)          # randlos
    root.attributes("-topmost", True)    # immer oben
    root.attributes("-alpha", 0.92)
    root.configure(bg=bg)

    label = tk.Label(
        root, text=text, fg="white", bg=bg,
        font=("Segoe UI", 14, "bold"), padx=24, pady=12,
    )
    label.pack()

    root.update_idletasks()
    w = root.winfo_width()
    sw = root.winfo_screenwidth()
    x = (sw - w) // 2
    root.geometry(f"+{x}+48")            # oben mittig

    if auto_close:
        root.after(auto_close, root.destroy)

    root.mainloop()


if __name__ == "__main__":
    main()
