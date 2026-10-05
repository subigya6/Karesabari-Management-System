from __future__ import annotations

import os
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
from typing import Optional

from theme import Colors, Fonts, Spacing, Radius
from leaf_analyzer import LeafAnalyzer, DiagnosisResult
import threading

class AILabFrame(ctk.CTkFrame):
    """AI Diagnosis Lab — upload plant images for disease detection."""

    def __init__(self, master: ctk.CTkFrame, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._analyzer = LeafAnalyzer() 
        self._current_image_path: Optional[str] = None
        self._photo_ref: Optional[ImageTk.PhotoImage] = None

        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(1, weight=1)

        # Hero Header
        hero = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Radius.LG, border_width=1, border_color=Colors.BORDER)
        hero.grid(row=0, column=0, columnspan=2, sticky="ew", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        hero.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hero, text="Plant AI Lab", font=(Fonts.FAMILY, 24, "bold"), text_color=Colors.PRIMARY_DARK).grid(row=0, column=0, sticky="w", padx=Spacing.LG, pady=(Spacing.MD, 2))
        ctk.CTkLabel(hero, text="Upload a photo of a plant part to detect disease and get organic remedy guidance.", font=(Fonts.FAMILY, Fonts.SIZE_BODY), text_color=Colors.TEXT_MUTED).grid(row=1, column=0, sticky="w", padx=Spacing.LG, pady=(0, Spacing.MD))

        # Left Panel (Image Preview & Controls)
        left = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Radius.LG, border_width=1, border_color=Colors.BORDER)
        left.grid(row=1, column=0, sticky="nsew", padx=(Spacing.LG, Spacing.SM), pady=Spacing.SM)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Plant Preview", font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"), text_color=Colors.ACCENT_BLUE).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        # Action Buttons & Organ Selector
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=Spacing.MD, pady=(0, Spacing.SM))
        actions.grid_columnconfigure(0, weight=1)

        upload_btn = ctk.CTkButton(
            actions, text="Upload Photo", height=40,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=Radius.MD, font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._upload_image,
        )
        upload_btn.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        # NEW: Organ Selector Dropdown
        self._organ_var = ctk.StringVar(value="leaf")
        organ_menu = ctk.CTkOptionMenu(
            actions, variable=self._organ_var,
            values=["auto", "leaf", "flower", "fruit", "bark"],
            width=100, height=40, corner_radius=Radius.MD,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY)
        )
        organ_menu.grid(row=0, column=1, padx=(0, Spacing.XS))

        ctk.CTkButton(
            actions, text="Reset", width=90, height=40,
            fg_color="#DCFCE7", hover_color="#BBF7D0", text_color=Colors.TEXT_DARK,
            corner_radius=Radius.MD, command=self._clear_image,
        ).grid(row=0, column=2, sticky="e")

        # Image Frame
        self._image_frame = ctk.CTkFrame(left, fg_color=Colors.BG_INPUT, corner_radius=Radius.LG, border_width=2, border_color=Colors.BORDER)
        self._image_frame.grid(row=2, column=0, sticky="nsew", padx=Spacing.MD)
        self._image_frame.grid_rowconfigure(0, weight=1)
        self._image_frame.grid_columnconfigure(0, weight=1)

        self._image_label = ctk.CTkLabel(self._image_frame, text="", font=(Fonts.FAMILY, Fonts.SIZE_BODY), text_color=Colors.TEXT_MUTED)
        self._image_label.grid(row=0, column=0, sticky="nsew", padx=Spacing.LG, pady=Spacing.LG)

        self._placeholder_label = ctk.CTkLabel(self._image_frame, text="📸", font=(Fonts.FAMILY, 54), text_color=Colors.TEXT_MUTED)
        self._placeholder_label.place(relx=0.5, rely=0.44, anchor="center")

        self._hint_label = ctk.CTkLabel(self._image_frame, text="No image loaded\nClick Upload to choose a photo", font=(Fonts.FAMILY, Fonts.SIZE_SMALL), text_color=Colors.TEXT_MUTED, justify="center")
        self._hint_label.place(relx=0.5, rely=0.72, anchor="center")

        self._file_meta_label = ctk.CTkLabel(left, text="No file selected", font=(Fonts.FAMILY, Fonts.SIZE_CAPTION), text_color=Colors.TEXT_MUTED, anchor="w")
        self._file_meta_label.grid(row=3, column=0, sticky="ew", padx=Spacing.MD, pady=(Spacing.XS, 0))

        self._scan_btn = ctk.CTkButton(
            left, text="Scan for Disease", height=44,
            fg_color=Colors.ACCENT_ORANGE, hover_color=Colors.EARTH_LIGHT,
            corner_radius=Radius.MD, font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            state="disabled", command=self._run_diagnosis,
        )
        self._scan_btn.grid(row=4, column=0, sticky="ew", padx=Spacing.MD, pady=(Spacing.SM, Spacing.MD))

        # Right Panel (Results)
        self._results_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Radius.LG, border_width=1, border_color=Colors.BORDER)
        self._results_frame.grid(row=1, column=1, sticky="nsew", padx=(Spacing.SM, Spacing.LG), pady=Spacing.SM)
        self._results_frame.grid_columnconfigure(0, weight=1)

        self._show_empty_results()

    def _upload_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Plant Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All files", "*.*")],
        )
        if not path:
            return

        self._current_image_path = path
        self._display_image(path)
        self._scan_btn.configure(state="normal")
        self._show_empty_results()

    def _clear_image(self) -> None:
        self._current_image_path = None
        self._photo_ref = None
        self._image_label.configure(image=None, text="")
        self._placeholder_label.place(relx=0.5, rely=0.44, anchor="center")
        self._hint_label.place(relx=0.5, rely=0.72, anchor="center")
        self._file_meta_label.configure(text="No file selected")
        self._scan_btn.configure(state="disabled", text="Scan for Disease")
        self._show_empty_results()

    def _display_image(self, path: str) -> None:
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((350, 350), Image.Resampling.LANCZOS)
            self._photo_ref = ImageTk.PhotoImage(img)
            self._image_label.configure(image=self._photo_ref, text="")
            self._placeholder_label.place_forget()
            self._hint_label.place_forget()
            self._file_meta_label.configure(text=os.path.basename(path))
        except Exception as e:
            self._image_label.configure(image=None, text=f"Error loading image:\n{e}")

    def _run_diagnosis(self) -> None:
        if not self._current_image_path:
            return

        # UPDATE: Inform the engine of the selected organ!
        self._analyzer.set_organ(self._organ_var.get())

        self._scan_btn.configure(state="disabled", text="Analyzing...")
        self.update_idletasks()

        def _worker(path: str):
            try:
                result = self._analyzer.predict(path)
                self.after(0, lambda r=result: self._show_results(r))
            except Exception as e:
                self.after(0, lambda msg=str(e): self._show_error(msg))
            finally:
                self.after(0, lambda: self._scan_btn.configure(state="normal", text="Scan for Disease"))

        threading.Thread(target=_worker, args=(self._current_image_path,), daemon=True).start()

    def _show_empty_results(self) -> None:
        for w in self._results_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(self._results_frame, text="Diagnosis Results", font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"), text_color=Colors.ACCENT_BLUE).pack(padx=Spacing.LG, pady=(Spacing.LG, Spacing.MD), anchor="w")

        guide = ctk.CTkFrame(self._results_frame, fg_color=Colors.BG_INPUT, corner_radius=Radius.MD, border_width=1, border_color=Colors.BORDER)
        guide.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.MD))
        ctk.CTkLabel(guide, text="How it works", font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"), text_color=Colors.TEXT_LIGHT, anchor="w").pack(anchor="w", padx=Spacing.MD, pady=(Spacing.SM, 2))
        ctk.CTkLabel(guide, text="1. Select the correct organ (leaf, fruit, etc.)\n2. Upload a clear photo\n3. Press Scan for Disease\n4. Review diagnosis and remedy", font=(Fonts.FAMILY, Fonts.SIZE_SMALL), text_color=Colors.TEXT_MUTED, justify="left", anchor="w").pack(anchor="w", padx=Spacing.MD, pady=(0, Spacing.SM))

        ctk.CTkLabel(self._results_frame, text="Result card will appear here after analysis.", font=(Fonts.FAMILY, Fonts.SIZE_SMALL), text_color=Colors.TEXT_MUTED).pack(padx=Spacing.LG, anchor="w")

    def _show_results(self, result: DiagnosisResult) -> None:
        for w in self._results_frame.winfo_children():
            w.destroy()
        pad = Spacing.LG

        ctk.CTkLabel(self._results_frame, text="Diagnosis Results", font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"), text_color=Colors.ACCENT_BLUE).pack(padx=pad, pady=(pad, Spacing.MD), anchor="w")
        ctk.CTkLabel(self._results_frame, text=f"🌱 Plant: {result.plant} ({result.organ})", font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"), text_color=Colors.PRIMARY_DARK).pack(padx=pad, pady=(0, Spacing.XS), anchor="w")

        disease_color = Colors.TEXT_SUCCESS if result.is_healthy else Colors.TEXT_DANGER
        state_card = ctk.CTkFrame(self._results_frame, fg_color=Colors.BG_INPUT, corner_radius=Radius.MD, border_width=1, border_color=Colors.BORDER)
        state_card.pack(fill="x", padx=pad, pady=(0, Spacing.MD))
        state_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(state_card, text=result.disease, font=(Fonts.FAMILY, 20, "bold"), text_color=disease_color, anchor="w").grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.SM, 2))
        ctk.CTkLabel(state_card, text=("Plant appears healthy" if result.is_healthy else "Potential disease detected"), font=(Fonts.FAMILY, Fonts.SIZE_SMALL), text_color=Colors.TEXT_MUTED, anchor="w").grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.SM))

        # Confidence handling
        conf_pct = result.confidence * 100
        ctk.CTkLabel(state_card, text=f"{conf_pct:.1f}% confidence", font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"), text_color=Colors.TEXT_DARK, fg_color=Colors.ACCENT_YELLOW, corner_radius=Radius.SM, padx=Spacing.SM, pady=2).grid(row=0, column=1, rowspan=2, sticky="e", padx=Spacing.MD)

        conf_frame = ctk.CTkFrame(self._results_frame, fg_color="transparent")
        conf_frame.pack(fill="x", padx=pad, pady=(0, Spacing.MD))
        ctk.CTkLabel(conf_frame, text=f"Confidence: {conf_pct:.1f}%", font=(Fonts.FAMILY, Fonts.SIZE_SMALL), text_color=Colors.TEXT_MUTED).pack(anchor="w")
        bar = ctk.CTkProgressBar(conf_frame, fg_color=Colors.BG_INPUT, progress_color=disease_color, height=10, corner_radius=Radius.SM)
        bar.pack(fill="x", pady=(Spacing.XS, 0))
        bar.set(result.confidence)

        # Remedy Card
        remedy_card = ctk.CTkFrame(self._results_frame, fg_color=Colors.BG_INPUT, corner_radius=Radius.MD, border_width=1, border_color=Colors.BORDER)
        remedy_card.pack(fill="x", padx=pad, pady=(0, pad))

        ctk.CTkLabel(remedy_card, text="Organic Remedy", font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"), text_color=Colors.PRIMARY_DARK).pack(padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS), anchor="w")
        
        # English Remedy
        ctk.CTkLabel(remedy_card, text=result.remedy_english, font=(Fonts.FAMILY, Fonts.SIZE_BODY), text_color=Colors.TEXT_LIGHT, wraplength=340, justify="left").pack(padx=Spacing.MD, pady=(0, Spacing.SM), anchor="w")
        
        # Nepali Remedy
        ctk.CTkLabel(remedy_card, text=result.remedy_nepali, font=(Fonts.FAMILY, Fonts.SIZE_BODY), text_color=Colors.ACCENT_YELLOW, wraplength=340, justify="left").pack(padx=Spacing.MD, pady=(0, Spacing.MD), anchor="w")

    def _show_error(self, error: str) -> None:
        for w in self._results_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(self._results_frame, text="Analysis Failed", font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"), text_color=Colors.TEXT_DANGER).pack(padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM), anchor="w")
        ctk.CTkLabel(self._results_frame, text=f"The AI encountered an issue:\n\n{error}", font=(Fonts.FAMILY, Fonts.SIZE_BODY), text_color=Colors.TEXT_LIGHT, wraplength=340, justify="left").pack(padx=Spacing.LG, anchor="w")