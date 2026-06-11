import sys
import tkinter as tk

# Standalone-Overlay: vom Tray per subprocess gestartet, damit tkinter im
# eigenen Hauptthread laeuft. Zeigt ein randloses, immer-im-Vordergrund
# Banner, das anzeigt dass eine Aufnahme laeuft. Wird beendet, indem der
# Elternprozess den Prozess terminiert (kein eigener Timer noetig).

_COLORS = {
    "recording": ("#F44336", "● Aufnahme läuft"),
    "processing": ("#FFC107", "● Wird verarbeitet…"),
}


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "recording"
    bg, default_text = _COLORS.get(mode, _COLORS["recording"])
    text = sys.argv[2] if len(sys.argv) > 2 else default_text

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

    root.mainloop()


if __name__ == "__main__":
    main()
