import customtkinter as ctk
from theme import Colors
from PIL import Image
import os
import sys


class SplashScreen(ctk.CTkFrame):
    # Set up this object and prepare its initial state
    def __init__(self, master, on_complete):
        super().__init__(master, fg_color=Colors.BG_DARK)
        self.on_complete = on_complete
        self._build_ui()

    # Build ui for this screen
    def _build_ui(self):
        self.grid_rowconfigure((0, 5), weight=1)
        self.grid_columnconfigure(0, weight=1)

        logo_path = os.path.join(os.path.dirname(__file__), "logo", "icon.png")
        try:
            pil_img = Image.open(logo_path)
            img = ctk.CTkImage(pil_img, size=(320, 320))
            label_text = ""
        except (FileNotFoundError, OSError):
            img = None
            label_text = "Karesabari"

        logo_card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=16)
        logo_card.grid(row=2, column=0, pady=(8, 0), padx=24)
        logo_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            logo_card,
            text=label_text,
            text_color=Colors.TEXT_DARK,
            image=img,
            fg_color="transparent",
            font=ctk.CTkFont(family="Segoe UI", size=42, weight="bold"),
        ).grid(row=0, column=0, pady=(12, 12), padx=16)

        ctk.CTkLabel(self, text="Smart Manager",
                      text_color=Colors.DARK_GREEN,
                      font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
                      ).grid(row=3, column=0, pady=(0, 4))
        ctk.CTkLabel(self, text="Your Smart Home Garden Companion",
                      text_color=Colors.TEXT_MUTED,
                      font=ctk.CTkFont(family="Segoe UI", size=13)
                      ).grid(row=4, column=0, pady=(0, 28))

        self.progress = ctk.CTkProgressBar(
            self, width=300, height=4,
            progress_color=Colors.PRIMARY, fg_color=Colors.BORDER,
            corner_radius=2)
        self.progress.grid(row=5, column=0)
        self.progress.set(0)

        self.status = ctk.CTkLabel(self, text="Initializing...",
                                    text_color=Colors.TEXT_MUTED,
                                    font=ctk.CTkFont(family="Segoe UI", size=11))
        self.status.grid(row=6, column=0, pady=(10, 0))

    # Handle start animation
    def start_animation(self):
        self._tick(0)

    # Handle tick
    def _tick(self, val):
        if val <= 1.0:
            self.progress.set(val)
            msgs = {
                0.0: "Initializing...",
                0.15: "Loading crop database...",
                0.3: "Preparing garden grid...",
                0.5: "Simulating weather patterns...",
                0.7: "Building developer tools...",
                0.85: "Almost ready...",
            }
            for t, m in msgs.items():
                if abs(val - t) < 0.015:
                    self.status.configure(text=m)
            self.after(20, self._tick, val + 0.01)
        else:
                self.after(20, self.on_complete)
   
    # Handle finish
    def _finish(self):
        self.on_complete()
