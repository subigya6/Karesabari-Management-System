"""
garden.py  Garden Management module for Karesabari.

Features:
  - Grid view of plant cards with live status badges
  - Add plant from catalogue (dropdown) or fully custom
  - Plant detail / edit dialog with watering history and check-in timeline
  - Inline water button on every card
  - Weekly check-in dialog
  - Status change dialog
  - Delete with confirmation
"""

from __future__ import annotations

import os
import calendar
import shutil
import uuid
import customtkinter as ctk
from PIL import Image
from customtkinter import CTkImage
from datetime import datetime
from typing import Callable, Optional
from tkinter import filedialog
import database as db

from theme import Colors, Fonts, Spacing, Radius


class GardenFrame(ctk.CTkFrame):
    """My Garden  grid view of all plants with management controls."""

    # Set up this object and prepare its initial state
    def __init__(self, master: ctk.CTkFrame, on_navigate: Optional[Callable] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_navigate = on_navigate

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        top.grid_columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            top, text="My Garden",
            font=(Fonts.FAMILY, Fonts.SIZE_TITLE, "bold"),
            text_color=Colors.PRIMARY_DARK, anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.grid(row=0, column=1)

        ctk.CTkButton(
            btn_frame, text="+ From Catalogue", width=140,
            fg_color=Colors.ACCENT_BLUE, hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._open_catalogue_add,
        ).pack(side="left", padx=(0, Spacing.SM))

        ctk.CTkButton(
            btn_frame, text="+ Custom Plant", width=130,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._open_custom_add,
        ).pack(side="left")

        self._stats_label = ctk.CTkLabel(
            self, text="", font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED, anchor="w",
        )
        self._stats_label.grid(row=1, column=0, sticky="w", padx=Spacing.LG)

        self._grid = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
        )
        self._grid.grid(row=2, column=0, sticky="nsew", padx=Spacing.LG, pady=Spacing.SM)

        self.refresh()


    # Refresh the current data
    def refresh(self) -> None:
        user = db.get_current_user()
        if user:
            family_name = user.get("family_name", f"Family {user.get('family_id', '')}")
            username = user.get("username", "User")
            self._title_label.configure(text=f"Welcome {username} | {family_name} Garden")
        else:
            self._title_label.configure(text="My Garden")

        for w in self._grid.winfo_children():
            w.destroy()

        plants = db.get_all_plants()
        healthy = sum(1 for p in plants if p.get("status") == "healthy")
        overdue = len(db.get_overdue_plants())
        self._stats_label.configure(
            text=f"{len(plants)} plant(s)  |  {healthy} healthy  |  {overdue} need water"
        )

        if not plants:
            empty_frame = ctk.CTkFrame(self._grid, fg_color="transparent")
            empty_frame.grid(row=0, column=0, sticky="nsew", pady=Spacing.XXL)
            self._grid.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                empty_frame,
                text="Your garden is empty.\nAdd a plant from the Catalogue or create a custom one!",
                font=(Fonts.FAMILY, Fonts.SIZE_BODY),
                text_color=Colors.TEXT_MUTED,
                justify="center",
            ).grid(row=0, column=0, sticky="nsew")

            empty_frame.grid_rowconfigure(0, weight=1)
            empty_frame.grid_columnconfigure(0, weight=1)

            self._create_empty_grid_cells(1, 0)
            return

        cols = 3
        for idx, plant in enumerate(plants):
            r, c = divmod(idx, cols)
            self._grid.grid_columnconfigure(c, weight=1)
            self._create_plant_card(r, c, plant)
            
        r, c = divmod(len(plants), cols)
        self._create_empty_grid_cells(r, c)

    
    # Create empty grid cells
    def _create_empty_grid_cells(self, start_row: int, start_col: int) -> None:
        cols = 3
        r, c = start_row, start_col
        
        self._grid.grid_columnconfigure(c, weight=1)
        
        card = ctk.CTkFrame(
            self._grid,
            fg_color=Colors.BG_CARD if str(ctk.get_appearance_mode()).lower() == "dark" else "#F9FAFB",  # soft grey card in light mode
            corner_radius=Radius.LG,
            border_width=1,
            border_color=Colors.BORDER,
        )
        card.grid(row=r, column=c, padx=Spacing.SM, pady=Spacing.SM, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        
        inner_frame = ctk.CTkFrame(card, fg_color="transparent")
        inner_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", pady=Spacing.XL)
        inner_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            inner_frame, text="Add New Plant",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.TEXT_MUTED,
        ).pack(pady=(0, Spacing.MD))
        
        btn_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        btn_frame.pack()
        
        ctk.CTkButton(
            btn_frame, text="+ From Catalogue", width=140,
            fg_color=Colors.ACCENT_BLUE, hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._open_catalogue_add,
        ).pack(pady=Spacing.XS)

        ctk.CTkButton(
            btn_frame, text="+ Custom Plant", width=140,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._open_custom_add,
        ).pack(pady=Spacing.XS)


    # Create plant card
    def _create_plant_card(self, row: int, col: int, plant: dict) -> None:
        is_overdue = False
        nw = plant.get("next_water_at")
        if nw:
            try:
                is_overdue = datetime.now() > datetime.fromisoformat(nw)
            except ValueError:
                pass

        light_mode = False
        try:
            light_mode = str(ctk.get_appearance_mode()).lower() == "light"
        except Exception:
            pass

        base_card_color = Colors.BG_CARD if not light_mode else "#F9FAFB"  # a touch darker than pure white

        card = ctk.CTkFrame(
            self._grid,
            fg_color=base_card_color,
            corner_radius=Radius.LG,
            border_width=2 if is_overdue else 1,
            border_color=Colors.TEXT_DANGER if is_overdue else Colors.BORDER,
        )
        card.grid(row=row, column=col, padx=Spacing.SM, pady=Spacing.SM, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)

        status_map = {
            "healthy":     (Colors.TEXT_SUCCESS, "Healthy"),
            "needs_water": (Colors.TEXT_WARNING, "Needs Water"),
            "sick":        (Colors.TEXT_DANGER,  "Sick"),
        }
        color, label = status_map.get(plant["status"], (Colors.TEXT_MUTED, plant["status"]))

        badge_frame = ctk.CTkFrame(card, fg_color="transparent")
        badge_frame.grid(row=0, column=0, sticky="ew", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        try:
            light_mode = str(ctk.get_appearance_mode()).lower() == "light"
        except Exception:
            light_mode = False

        outline_color = "#000000" if light_mode else color
        border_w = 1 if light_mode else 0

        badge_wrapper = ctk.CTkFrame(badge_frame, fg_color=color, corner_radius=Radius.SM, border_width=border_w, border_color=outline_color)
        badge_wrapper.pack(side="left")

        ctk.CTkLabel(
            badge_wrapper, text=f"  {label}  ",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            fg_color="transparent", 
            text_color=Colors.BG_DARK, height=22,
        ).pack()

        streak = plant.get("streak", 0)
        if streak > 0:
            ctk.CTkLabel(
                badge_frame, text=f"  {streak}x streak  ",
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
                fg_color=Colors.ACCENT_YELLOW, corner_radius=Radius.SM,
                text_color=Colors.BG_DARK, height=22,
            ).pack(side="left", padx=(Spacing.XS, 0))

        ctk.CTkButton(
            badge_frame,
            text="✕",
            width=28,
            height=24,
            fg_color=Colors.TEXT_DANGER,
            hover_color="#E53935",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=lambda p=plant: self._confirm_delete(p),
        ).pack(side="right", padx=(Spacing.XS, 0))

        name_text = plant["name"]
        if plant.get("name_nepali"):
            name_text += f"\n{plant['name_nepali']}"
        ctk.CTkLabel(
            card, text=name_text,
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.TEXT_LIGHT, anchor="w", justify="left",
        ).grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=Spacing.XS)

        freq_h = plant.get("water_freq_hours", 24)
        if freq_h < 24:
            freq_str = f"Every {int(freq_h)}h"
        elif freq_h == 24:
            freq_str = "Daily"
        else:
            freq_str = f"Every {int(freq_h / 24)}d"

        meta = f"Watered: {freq_str}  |  Waterings: {plant.get('total_waterings', 0)}"
        ctk.CTkLabel(
            card, text=meta,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
            text_color=Colors.TEXT_MUTED, anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.XS))

        planted = plant.get("planted_on", "")[:10] if plant.get("planted_on") else "Unknown"
        ctk.CTkLabel(
            card, text=f"Planted: {planted}",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
            text_color=Colors.TEXT_MUTED, anchor="w",
        ).grid(row=3, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.XS))

        if plant.get("notes"):
            ctk.CTkLabel(
                card, text=plant["notes"],
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                text_color=Colors.TEXT_MUTED, anchor="w", wraplength=200,
            ).grid(row=4, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.XS))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="ew", padx=Spacing.MD, pady=(Spacing.SM, Spacing.MD))

        water_color = Colors.TEXT_DANGER if is_overdue else Colors.PRIMARY
        ctk.CTkButton(
            btn_frame, text="Water", height=32, width=74,
            fg_color=water_color, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=lambda p=plant: self._quick_water(p),
        ).pack(side="left", padx=(0, Spacing.XS))

        ctk.CTkButton(
            btn_frame, text="Details", height=32, width=74,
            fg_color=Colors.ACCENT_BLUE, hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=lambda p=plant: self._open_detail(p),
        ).pack(side="left", padx=(0, Spacing.XS))

        ctk.CTkButton(
            btn_frame, text="Check-in", height=32, width=82,
            fg_color=Colors.EARTH, hover_color=Colors.EARTH_LIGHT,
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=lambda p=plant: self._open_checkin(p),
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="✕", height=32, width=32,
            fg_color=Colors.TEXT_DANGER, hover_color="#E53935",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=lambda p=plant: self._confirm_delete(p),
        ).pack(side="right")

        try:
            # Handle find image for plant
            def find_image_for_plant(p: dict) -> str | None:
                base = os.path.dirname(__file__)
                candidates = []
                if p.get("image_path"):
                    candidates.append(os.path.join(base, p.get("image_path")))
                if p.get("icon_path"):
                    candidates.append(os.path.join(base, p.get("icon_path")))
                try:
                    pid = int(p.get("catalogue_id") or p.get("id"))
                    candidates.append(os.path.join(base, "assets", "catalogue", f"{pid}.png"))
                except Exception:
                    pass
                name_slug = (p.get("name") or "").lower().replace(" ", "_")
                if name_slug:
                    candidates.append(os.path.join(base, "assets", "catalogue", f"{name_slug}.png"))
                    candidates.append(os.path.join(base, "logo", f"{name_slug}.png"))

                candidates.append(os.path.join(base, "logo", "logo.png"))

                for c in candidates:
                    if c and os.path.isfile(c):
                        return c
                return None

            img_path = find_image_for_plant(plant)
            if img_path:
                try:
                    with Image.open(img_path) as _img:
                        pil = _img.convert("RGBA").copy()
                    try:
                        from PIL import ImageDraw
                        w, h = pil.size
                        radius = min(w, h) // 6
                        mask = Image.new("L", (w, h), 0)
                        draw = ImageDraw.Draw(mask)
                        draw.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
                        pil.putalpha(mask)
                    except Exception:
                        pass
                    tk_img = CTkImage(pil, size=(84, 84))
                    lbl = ctk.CTkLabel(card, image=tk_img, text="", width=84, height=84)
                    lbl.grid(row=1, column=1, rowspan=5, sticky="ne", padx=Spacing.MD, pady=Spacing.MD)
                    lbl._img_ref = tk_img
                except Exception:
                    placeholder = ctk.CTkLabel(card, text="", width=84, height=84, fg_color=Colors.BG_INPUT, corner_radius=12)
                    placeholder.grid(row=1, column=1, rowspan=5, sticky="ne", padx=Spacing.MD, pady=Spacing.MD)
                    placeholder._img_ref = None
            else:
                placeholder = ctk.CTkLabel(card, text="", width=84, height=84, fg_color=Colors.BG_INPUT, corner_radius=12)
                placeholder.grid(row=1, column=1, rowspan=5, sticky="ne", padx=Spacing.MD, pady=Spacing.MD)
                placeholder._img_ref = None
        except Exception:
            pass

        name_text = plant["name"]
        if plant.get("name_nepali"):
            name_text += f" ({plant['name_nepali']})"
        
        ctk.CTkLabel(
            card, text=name_text,
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.TEXT_LIGHT, anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.XS, 0))

        sci_name = plant.get("scientific_name", "")
        if sci_name:
            ctk.CTkLabel(
                card, text=sci_name,
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "italic"),
                text_color=Colors.TEXT_MUTED, anchor="w",
            ).grid(row=2, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.XS))


    # Handel quick water
    def _quick_water(self, plant: dict) -> None:
        result = db.mark_watered(plant["id"])
        if result:
            on_time = result.get("on_time", True)
            streak = result.get("streak", 0)
            msg_type = "success" if on_time else "warning"
            text = f"'{plant['name']}' watered! Streak: {streak}" if on_time else \
                   f"'{plant['name']}' watered late. Streak reset to {streak}."
            db.add_message(text, "Garden", msg_type)
        self.refresh()
        self._notify_dashboard()

    # Handle confirm delete
    def _confirm_delete(self, plant: dict) -> None:
        dialog = _ConfirmDeleteDialog(self, plant)
        self.wait_window(dialog)
        if dialog.confirmed:
            db.delete_plant(plant["id"])
            db.add_message(f"'{plant['name']}' removed from garden.", "Garden", "warning")
            self.refresh()
            self._notify_dashboard()

    # Open detail
    def _open_detail(self, plant: dict) -> None:
        dialog = _PlantDetailDialog(self, plant, on_back_to_dashboard=self._go_dashboard)
        self.wait_window(dialog)
        self.refresh()
        self._notify_dashboard()

    # Handle go dashboard
    def _go_dashboard(self) -> None:
        if self._on_navigate:
            self._on_navigate("go_garden")

    # Open checkin
    def _open_checkin(self, plant: dict) -> None:
        dialog = _CheckinDialog(self, plant)
        self.wait_window(dialog)
        self.refresh()
        self._notify_dashboard()

    # Open catalogue add
    def _open_catalogue_add(self) -> None:
        dialog = _CatalogueAddDialog(self)
        self.wait_window(dialog)
        self.refresh()
        self._notify_dashboard()

    # Open custom add
    def _open_custom_add(self) -> None:
        dialog = _CustomAddDialog(self)
        self.wait_window(dialog)
        self.refresh()
        self._notify_dashboard()

    # Handle notify dashboard
    def _notify_dashboard(self) -> None:
        if self._on_navigate:
            self._on_navigate("refresh_dashboard")

    # Save custom plant
    def _save_custom_plant(self, dialog, data):
        db.sync_to_catalogue(data)
        
        db.add_plant(data)
        dialog.destroy()
        self.refresh()


class _CatalogueAddDialog(ctk.CTkToplevel):
    """Pick a plant from the catalogue and add it to the garden (card-based)."""

    CARD_COLS = 3

    # Set up this object and prepare its initial state
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add from Catalogue")
        self.geometry("900x560")
        self.minsize(800, 500)
        self.configure(fg_color=Colors.BG_CARD)
        self.grab_set()
        
        pad = Spacing.LG
        self._items = db.search_catalogue()
        self._filtered_items = list(self._items)
        self._selected_id: Optional[int] = None
        self._image_cache: dict[str, object] = {}
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=pad, pady=(pad, Spacing.SM))
        header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header, text="Add from Catalogue",
            font=(Fonts.FAMILY, Fonts.SIZE_TITLE, "bold"),
            text_color=Colors.PRIMARY_DARK,
        ).grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(
            header, text="Browse vegetables and pick one to plant in your garden.",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(Spacing.XS, 0))
        
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", padx=pad, pady=(0, Spacing.SM))
        controls.grid_columnconfigure(0, weight=1)
        
        self._search = ctk.CTkEntry(
            controls,
            placeholder_text="Search by name, Nepali name, or season...",
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
            height=34,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY),
        )
        self._search.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.SM))
        self._search.bind("<KeyRelease>", lambda e: self._filter())
        
        self._season_var = ctk.StringVar(value="All")
        self._chips: list[ctk.CTkButton] = []
        chip_frame = ctk.CTkFrame(controls, fg_color="transparent")
        chip_frame.grid(row=0, column=1, sticky="e")
        for idx, season in enumerate(["All", "Summer", "Winter", "Monsoon"]):
            btn = ctk.CTkButton(
                chip_frame, text=season, width=70, height=26,
                fg_color=Colors.PRIMARY if season == "All" else Colors.BG_INPUT,
                hover_color=Colors.PRIMARY_HOVER,
                corner_radius=Radius.XL,
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
                command=lambda s=season: self._filter_season(s),
            )
            btn.grid(row=0, column=idx, padx=Spacing.XS)
            self._chips.append(btn)
        
        self._grid = ctk.CTkScrollableFrame(
            self,
            fg_color=Colors.BG_DARK if str(ctk.get_appearance_mode()).lower() == "dark" else Colors.BG_LIGHT,
            corner_radius=Radius.MD,
        )
        self._grid.grid(row=2, column=0, sticky="nsew", padx=pad, pady=(0, pad))
        for c in range(self.CARD_COLS):
            self._grid.grid_columnconfigure(c, weight=1)
        
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=pad, pady=(0, pad))
        footer.grid_columnconfigure(0, weight=1)
        
        self._status = ctk.CTkLabel(
            footer, text="Select a plant card to continue.",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
        )
        self._status.grid(row=0, column=0, sticky="w")
        
        btn_row = ctk.CTkFrame(footer, fg_color="transparent")
        btn_row.grid(row=0, column=1, sticky="e")
        
        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            text_color=Colors.TEXT_DARK,
            command=self.destroy,
            width=90,
            height=32,
        ).pack(side="right", padx=(Spacing.XS, 0))
        
        ctk.CTkButton(
            btn_row, text="Add Plant",
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            command=self._save,
            width=110,
            height=32,
        ).pack(side="right", padx=(0, Spacing.XS))
        
        self._build_cards()


    # Filter season
    def _filter_season(self, season: str) -> None:
        self._season_var.set(season)
        seasons = ["All", "Summer", "Winter", "Monsoon"]
        for btn, s in zip(self._chips, seasons):
            btn.configure(fg_color=Colors.PRIMARY if s == season else Colors.BG_INPUT)
        self._filter()

    # Filter the current data
    def _filter(self) -> None:
        query = self._search.get().strip().lower()
        season = self._season_var.get()
        filtered: list[dict] = []
        for item in self._items:
            name = item.get("name", "").lower()
            nep = (item.get("name_nepali") or "").lower()
            seas = (item.get("season") or "").lower()
            if query and query not in name and query not in nep and query not in seas:
                continue
            if season != "All" and item.get("season") != season:
                continue
            filtered.append(item)
        self._filtered_items = filtered
        self._build_cards()

    # Build cards for this screen
    def _build_cards(self) -> None:
        for w in self._grid.winfo_children():
            w.destroy()

        if not self._filtered_items:
            ctk.CTkLabel(
                self._grid,
                text="No vegetables found. Try a different search.",
                font=(Fonts.FAMILY, Fonts.SIZE_BODY),
                text_color=Colors.TEXT_MUTED,
            ).grid(row=0, column=0, padx=Spacing.LG, pady=Spacing.LG)
            return

        # Handle find icon path
        def _find_icon_path(it: dict) -> Optional[str]:
            base = os.path.dirname(__file__)
            candidates = []
            if it.get("image_path"):
                candidates.append(os.path.join(base, it.get("image_path")))
            slug = (it.get("name") or "").lower().replace(" ", "_")
            if slug:
                candidates.append(os.path.join(base, "logo", f"{slug}.png"))
                candidates.append(os.path.join(base, "assets", "catalogue", f"{slug}.png"))
            candidates.append(os.path.join(base, "logo", "logo.png"))
            for p in candidates:
                if p and os.path.isfile(p):
                    return p
            return None

        # Return ctk image
        def _get_ctk_image(path: str, size: tuple[int, int]):
            if not path:
                return None
            key = f"{path}:{size[0]}x{size[1]}"
            if key in self._image_cache:
                return self._image_cache[key]
            try:
                with Image.open(path) as im:
                    pil = im.convert("RGBA").copy()
                try:
                    pil = pil.resize((size[0], size[1]), Image.LANCZOS)
                except Exception:
                    pass
                try:
                    from PIL import ImageDraw
                    w, h = pil.size
                    radius = min(w, h) // 6
                    mask = Image.new("L", (w, h), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
                    pil.putalpha(mask)
                except Exception:
                    pass
                tk_img = CTkImage(pil, size=size)
                self._image_cache[key] = tk_img
                return tk_img
            except Exception:
                return None
        for idx, item in enumerate(self._filtered_items):
            row = idx // self.CARD_COLS
            col = idx % self.CARD_COLS

            is_selected = self._selected_id == item.get("id")
            border_color = Colors.PRIMARY if is_selected else Colors.BORDER

            card = ctk.CTkFrame(
                self._grid,
                fg_color=Colors.BG_CARD,
                corner_radius=Radius.LG,
                border_width=2,
                border_color=border_color,
            )
            card.grid(row=row, column=col, padx=Spacing.SM, pady=Spacing.SM, sticky="nsew")
            card.grid_columnconfigure(1, weight=1)

            icon_path = _find_icon_path(item)
            tk_img = _get_ctk_image(icon_path, (96, 96)) if icon_path else None
            if tk_img:
                icon = ctk.CTkLabel(card, image=tk_img, text="", width=96, height=96)
                icon._img_ref = tk_img
                icon.grid(row=0, column=0, rowspan=2, padx=Spacing.MD, pady=Spacing.MD, sticky="n")
            else:
                icon = ctk.CTkLabel(
                    card, text="🌱", width=64, height=64,
                    corner_radius=32, fg_color=Colors.PRIMARY_DARK,
                    text_color=Colors.TEXT_LIGHT,
                    font=(Fonts.FAMILY, 18, "bold"),
                )
                icon.grid(row=0, column=0, rowspan=2, padx=Spacing.MD, pady=Spacing.MD, sticky="n")

            title = item.get("name", "")
            nep = item.get("name_nepali") or ""
            if nep:
                title = f"{title} ({nep})"
            ctk.CTkLabel(
                card, text=title,
                font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
                text_color=Colors.TEXT_LIGHT,
                anchor="w",
            ).grid(row=0, column=1, sticky="ew", padx=(0, Spacing.MD), pady=(Spacing.MD, 0))

            season = item.get("season", "All")
            water_need = item.get("water_need", "medium")
            freq = item.get("water_freq_hours", 24)
            meta = f"Season: {season}  |  Water: {water_need}  |  Every {int(freq)}h"
            ctk.CTkLabel(
                card, text=meta,
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
                text_color=Colors.TEXT_SECONDARY,
                anchor="w",
            ).grid(row=1, column=1, sticky="ew", padx=(0, Spacing.MD), pady=(0, Spacing.XS))

            desc = item.get("description") or "No description available."
            ctk.CTkLabel(
                card, text=desc,
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                text_color=Colors.TEXT_MUTED,
                wraplength=220,
                justify="left",
                anchor="w",
            ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=Spacing.MD, pady=(0, Spacing.MD))

            # React when click
            def on_click(_evt, it=item):
                self._selected_id = it.get("id")
                self._status.configure(
                    text=f"Selected: {it.get('name')} ({it.get('name_nepali', '')})",
                    text_color=Colors.TEXT_MUTED,
                )
                self._build_cards()

            card.bind("<Button-1>", on_click)
            for child in card.winfo_children():
                child.bind("<Button-1>", on_click)

    # Save the current data
    def _save(self) -> None:
        if not self._selected_id:
            self._status.configure(
                text="Please select a plant card first.",
                text_color=Colors.TEXT_WARNING,
            )
            return
        db.add_plant_from_catalogue(self._selected_id, "")
        self.destroy()



class _CustomAddDialog(ctk.CTkToplevel):
    """Create a fully custom plant."""

    # Set up this object and prepare its initial state
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create Custom Plant")
        self.geometry("720x670")
        self.minsize(680, 620)
        self.configure(fg_color=Colors.BG_CARD)
        self.grab_set()
        self._image_preview_ref: Optional[CTkImage] = None
        self._image_path_var = ctk.StringVar(value="")

        pad = Spacing.LG

        ctk.CTkLabel(self, text="Create Custom Plant",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.PRIMARY_DARK).pack(pady=(pad, Spacing.MD))

        self._name = self._field("Plant Name *", "e.g. Sweet Basil")
        self._nepali = self._field("Nepali Name", "e.g. Tulsi")
        ctk.CTkLabel(self, text="Watering Frequency (hours)",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=pad)
        self._freq_slider = ctk.CTkSlider(
            self, from_=1, to=168, number_of_steps=41,
            fg_color=Colors.BG_INPUT, progress_color=Colors.PRIMARY,
            button_color=Colors.PRIMARY_DARK, button_hover_color=Colors.PRIMARY,
            command=self._on_freq_change,
        )
        self._freq_slider.set(24)
        self._freq_slider.pack(fill="x", padx=pad, pady=(2, 0))
        self._freq_label = ctk.CTkLabel(self, text="Every 24 hours (daily)",
                                         font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
                                         text_color=Colors.TEXT_MUTED)
        self._freq_label.pack(anchor="w", padx=pad, pady=(0, Spacing.SM))

        ctk.CTkLabel(self, text="Water Need",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=pad)
        self._water_need = ctk.CTkOptionMenu(
            self, values=["low", "medium", "high"],
            fg_color=Colors.BG_INPUT, button_color=Colors.PRIMARY,
            button_hover_color=Colors.PRIMARY_HOVER, corner_radius=Radius.SM,
            text_color="black",
        )
        self._water_need.set("medium")
        self._water_need.pack(fill="x", padx=pad, pady=(2, Spacing.SM))

        ctk.CTkLabel(self, text="Season",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=pad)
        self._season = ctk.CTkOptionMenu(
            self, values=["Summer", "Winter", "Monsoon", "All Year"],
            fg_color=Colors.BG_INPUT, button_color=Colors.PRIMARY,
            button_hover_color=Colors.PRIMARY_HOVER, corner_radius=Radius.SM,
            text_color="black",
        )
        self._season.pack(fill="x", padx=pad, pady=(2, Spacing.SM))

        self._notes = self._field("Notes", "Any special care instructions...")

        ctk.CTkLabel(
            self,
            text="Plant Image",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=pad)

        img_row = ctk.CTkFrame(self, fg_color="transparent")
        img_row.pack(fill="x", padx=pad, pady=(2, Spacing.XS))
        img_row.grid_columnconfigure(0, weight=1)

        self._image_entry = ctk.CTkEntry(
            img_row,
            textvariable=self._image_path_var,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
            placeholder_text="No image selected",
        )
        self._image_entry.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        ctk.CTkButton(
            img_row,
            text="Upload File",
            width=110,
            fg_color=Colors.ACCENT_BLUE,
            hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            command=self._upload_image,
        ).grid(row=0, column=1, sticky="e", padx=(0, Spacing.XS))

        ctk.CTkButton(
            img_row,
            text="Take Photo",
            width=100,
            fg_color=Colors.ACCENT_ORANGE,
            hover_color=Colors.EARTH_LIGHT,
            corner_radius=Radius.SM,
            command=self._take_photo,
        ).grid(row=0, column=2, sticky="e")

        preview_row = ctk.CTkFrame(self, fg_color="transparent")
        preview_row.pack(fill="x", padx=pad, pady=(0, Spacing.SM))

        self._image_preview = ctk.CTkLabel(
            preview_row,
            text="No image selected",
            width=120,
            height=96,
            fg_color=Colors.BG_INPUT,
            corner_radius=Radius.SM,
            text_color=Colors.TEXT_MUTED,
        )
        self._image_preview.pack(anchor="w")

        ctk.CTkButton(
            preview_row,
            text="Clear Image",
            width=100,
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=self._clear_image,
        ).pack(anchor="w", pady=(Spacing.XS, 0))

        ctk.CTkButton(
            self, text="Plant It!", fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER, corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._save,
        ).pack(pady=Spacing.MD)

    # Copy image to store
    def _copy_image_to_store(self, src_path: str) -> str:
        base_dir = os.path.dirname(__file__)
        store_dir = os.path.join(base_dir, "uploads", "plants")
        os.makedirs(store_dir, exist_ok=True)
        ext = os.path.splitext(src_path)[1].lower() or ".jpg"
        name = f"custom_{uuid.uuid4().hex[:10]}{ext}"
        target = os.path.join(store_dir, name)
        shutil.copy2(src_path, target)
        return os.path.relpath(target, base_dir)

    # Handle upload image
    def _upload_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Plant Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            saved = self._copy_image_to_store(path)
            self._image_path_var.set(saved)
            self._refresh_image_preview()
        except Exception:
            return

    # Handle take photo
    def _take_photo(self) -> None:
        try:
            import cv2  # type: ignore
        except Exception:
            self._upload_image()
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release()
            self._upload_image()
            return

        captured_path = ""
        window = "Take Photo (SPACE: capture, ESC: cancel)"
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                cv2.imshow(window, frame)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    break
                if key == 32:
                    base_dir = os.path.dirname(__file__)
                    store_dir = os.path.join(base_dir, "uploads", "plants")
                    os.makedirs(store_dir, exist_ok=True)
                    filename = f"custom_{uuid.uuid4().hex[:10]}.jpg"
                    captured_path = os.path.join(store_dir, filename)
                    cv2.imwrite(captured_path, frame)
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

        if captured_path:
            self._image_path_var.set(os.path.relpath(captured_path, os.path.dirname(__file__)))
            self._refresh_image_preview()

    # Clear image
    def _clear_image(self) -> None:
        self._image_path_var.set("")
        self._refresh_image_preview()

    # Refresh image preview now
    def _refresh_image_preview(self) -> None:
        path = (self._image_path_var.get() or "").strip()
        if not path:
            self._image_preview_ref = None
            self._image_preview.configure(image=None, text="No image selected")
            return

        abs_path = path if os.path.isabs(path) else os.path.join(os.path.dirname(__file__), path)
        if not os.path.exists(abs_path):
            self._image_preview_ref = None
            self._image_preview.configure(image=None, text="Image not found")
            return

        try:
            with Image.open(abs_path) as img:
                pil = img.convert("RGBA")
                pil.thumbnail((120, 96), Image.Resampling.LANCZOS)
            self._image_preview_ref = CTkImage(pil, size=pil.size)
            self._image_preview.configure(image=self._image_preview_ref, text="")
        except Exception:
            self._image_preview_ref = None
            self._image_preview.configure(image=None, text="Invalid image")

    # Handle field
    def _field(self, label: str, placeholder: str = "") -> ctk.CTkEntry:
        pad = Spacing.LG
        ctk.CTkLabel(self, text=label,
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=pad)
        entry = ctk.CTkEntry(self, fg_color=Colors.BG_INPUT,
                              border_color=Colors.BORDER, corner_radius=Radius.SM,
                              placeholder_text=placeholder)
        entry.pack(fill="x", padx=pad, pady=(2, Spacing.SM))
        return entry

    # React when freq change
    def _on_freq_change(self, val: float) -> None:
        h = int(val)
        if h < 24:
            text = f"Every {h} hours"
        elif h == 24:
            text = "Every 24 hours (daily)"
        elif h < 168:
            text = f"Every {h} hours ({h // 24}d {h % 24}h)"
        else:
            text = "Every 168 hours (weekly)"
        self._freq_label.configure(text=text)

    # Save the current data
    def _save(self) -> None:
        name = self._name.get().strip()
        if not name:
            return
        
        freq = int(self._freq_slider.get())
        season = self._season.get()
        water_need = self._water_need.get()
        notes = self._notes.get().strip()
        nepali = self._nepali.get().strip()

        db.add_catalogue_item(
            name=name,
            name_nepali=nepali,
            season=season,
            water_need=water_need,
            water_freq_hours=freq,
            description=notes,
        )

        pid = db.add_plant(
            name=name,
            name_nepali=nepali,
            water_freq_hours=freq,
            notes=notes,
            season=season,
            water_need=water_need,
            image_path=(self._image_path_var.get() or "").strip(),
        )
        db.add_message(f"Custom plant '{name}' added to garden and catalogue!", "Garden", "success")
        self.destroy()



class _FloatingModal(ctk.CTkFrame):
    """In-window floating modal with dim backdrop (single-window UX)."""

    # Set up this object and prepare its initial state
    def __init__(self, parent, width: int, height: int, title: str = ""):
        self._owner = parent.winfo_toplevel()
        self._title = title

        self._backdrop = ctk.CTkFrame(self._owner, fg_color="#0A0F1C", corner_radius=0)
        self._backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._backdrop.lift()
        self._backdrop.bind("<Button-1>", lambda _e: "break")

        super().__init__(
            self._backdrop,
            fg_color=Colors.BG_DARK,
            corner_radius=Radius.LG,
            border_width=1,
            border_color=Colors.BORDER,
            width=width,
            height=height,
        )
        self._width = width
        self._height = height
        self.place(relx=0.5, rely=0.5, anchor="center")
        self.pack_propagate(False)
        self.lift()

        self._esc_bind = self._owner.bind("<Escape>", lambda _e: self.destroy(), add="+")

        self._close_btn = ctk.CTkButton(
            self,
            text="X",
            width=30,
            height=28,
            corner_radius=Radius.SM,
            fg_color=Colors.BG_INPUT,
            hover_color=Colors.BORDER,
            text_color=Colors.TEXT_LIGHT,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self.destroy,
        )
        self._close_btn.place(relx=1.0, x=-12, y=10, anchor="ne")
        self._close_btn.lift()

    # Handle destroy
    def destroy(self):
        try:
            if self._esc_bind:
                self._owner.unbind("<Escape>", self._esc_bind)
        except Exception:
            pass

        try:
            super().destroy()
        except Exception:
            pass

        try:
            if self._backdrop is not None and self._backdrop.winfo_exists():
                self._backdrop.destroy()
        except Exception:
            pass

class _PlantDetailDialog(_FloatingModal):
    """Detailed view of a plant with watering history, check-ins, and edit."""

    # Set up this object and prepare its initial state
    def __init__(self, parent, plant: dict, on_back_to_dashboard: Optional[Callable[[], None]] = None):
        super().__init__(parent, width=900, height=760, title=f"Plant Details: {plant['name']}")
        self._plant_id = plant["id"]
        self._deleted = False
        self._photo_ref: Optional[CTkImage] = None
        self._on_back_to_dashboard = on_back_to_dashboard

        self._build_ui()

    # Handle resolve plant image path
    def _resolve_plant_image_path(self, plant: dict) -> Optional[str]:
        explicit = (plant.get("image_path") or "").strip()
        if explicit:
            if os.path.exists(explicit):
                return explicit
            rel = os.path.join(os.path.dirname(__file__), explicit)
            if os.path.exists(rel):
                return rel

        base_dir = os.path.dirname(__file__)
        logo_dir = os.path.join(base_dir, "logo")
        raw = (plant.get("slug") or plant.get("name") or "").strip().lower()
        slug = "".join(ch if ch.isalnum() else "_" for ch in raw).strip("_")
        if slug:
            for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                candidate = os.path.join(logo_dir, f"{slug}{ext}")
                if os.path.exists(candidate):
                    return candidate

        generic = os.path.join(logo_dir, "logo.png")
        if os.path.exists(generic):
            return generic
        return None

    # Load detail image into this view
    def _load_detail_image(self, path: Optional[str], size: tuple[int, int] = (110, 110)) -> Optional[CTkImage]:
        if not path:
            return None
        try:
            with Image.open(path) as img:
                image = img.convert("RGBA")
                image.thumbnail(size, Image.Resampling.LANCZOS)
                return CTkImage(image, size=image.size)
        except Exception:
            return None

    # Handle deleted
    @property
    def deleted(self) -> bool:
        return self._deleted

    # Build ui for this screen
    def _build_ui(self) -> None:
        plant = db.get_plant(self._plant_id)
        if not plant:
            return

        for w in self.winfo_children():
            w.destroy()

        pad = Spacing.LG

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=pad, pady=(pad, Spacing.SM))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Plant Details",
            font=(Fonts.FAMILY, 22, "bold"),
            text_color=Colors.PRIMARY_DARK,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        header_actions = ctk.CTkFrame(header, fg_color="transparent")
        header_actions.grid(row=0, column=2, sticky="e")

        ctk.CTkButton(
            header_actions,
            text="Back to Dashboard",
            height=30,
            fg_color=Colors.ACCENT_BLUE,
            hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            command=self._back_to_dashboard,
        ).pack(side="right")

        status_map = {
            "healthy": (Colors.TEXT_SUCCESS, "Healthy"),
            "needs_water": (Colors.TEXT_WARNING, "Needs Water"),
            "sick": (Colors.TEXT_DANGER, "Sick"),
        }
        color, label = status_map.get(plant["status"], (Colors.TEXT_MUTED, plant["status"]))
        ctk.CTkLabel(
            header,
            text=f"  {label}  ",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            fg_color=color,
            corner_radius=Radius.SM,
            text_color=Colors.BG_DARK,
            height=24,
        ).grid(row=0, column=1, sticky="e", padx=(0, Spacing.SM))

        content = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=pad, pady=(0, Spacing.XS))
        content.grid_columnconfigure(0, weight=1)

        media = ctk.CTkFrame(
            content,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.MD,
            border_width=1,
            border_color=Colors.BORDER,
        )
        media.pack(fill="x", pady=(0, Spacing.XS))
        media.grid_columnconfigure(1, weight=1)

        image_host = ctk.CTkFrame(media, fg_color=Colors.BG_INPUT, corner_radius=Radius.MD)
        image_host.grid(row=0, column=0, padx=Spacing.SM, pady=Spacing.SM, sticky="nsew")
        image_host.grid_rowconfigure(0, weight=1)
        image_host.grid_columnconfigure(0, weight=1)

        image_path = self._resolve_plant_image_path(plant)
        self._photo_ref = self._load_detail_image(image_path)
        if self._photo_ref is not None:
            ctk.CTkLabel(image_host, text="", image=self._photo_ref).grid(
                row=0, column=0, padx=Spacing.XS, pady=Spacing.XS
            )
        else:
            ctk.CTkLabel(
                image_host,
                text="PLANT",
                font=(Fonts.FAMILY, 22, "bold"),
                text_color=Colors.TEXT_MUTED,
            ).grid(row=0, column=0, padx=Spacing.SM, pady=Spacing.SM)

        summary = ctk.CTkFrame(media, fg_color="transparent")
        summary.grid(row=0, column=1, sticky="nsew", padx=(0, Spacing.SM), pady=Spacing.SM)

        ctk.CTkLabel(
            summary,
            text=plant.get("name") or "Plant",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.TEXT_LIGHT,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            summary,
            text=(plant.get("scientific_name") or "").strip() or "No scientific name",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "italic"),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w", pady=(2, Spacing.XS))
        ctk.CTkLabel(
            summary,
            text=(plant.get("description") or plant.get("notes") or "No description added.")[:180],
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_SECONDARY,
            justify="left",
            wraplength=480,
            anchor="w",
        ).pack(anchor="w")

        identity = ctk.CTkFrame(
            content,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.MD,
            border_width=1,
            border_color=Colors.BORDER,
        )
        identity.pack(fill="x", pady=(0, Spacing.XS))
        identity.grid_columnconfigure((0, 1, 2), weight=1)

        blocks = [
            ("General Name", plant.get("name") or "-", Colors.TEXT_LIGHT),
            ("Nepali Name", plant.get("name_nepali") or "-", Colors.ACCENT_YELLOW),
            ("Scientific Name", plant.get("scientific_name") or "-", Colors.ACCENT_BLUE),
        ]
        for i, (title, value, value_color) in enumerate(blocks):
            b = ctk.CTkFrame(identity, fg_color="transparent")
            b.grid(row=0, column=i, sticky="ew", padx=Spacing.MD, pady=Spacing.MD)
            ctk.CTkLabel(
                b,
                text=title,
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                b,
                text=value,
                font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold" if i == 0 else "normal"),
                text_color=value_color,
                anchor="w",
                wraplength=220,
                justify="left",
            ).pack(anchor="w", pady=(2, 0))

        stats_frame = ctk.CTkFrame(content, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, Spacing.XS))

        stats = [
            ("Streak", str(plant.get("streak", 0)), Colors.ACCENT_YELLOW),
            ("Best", str(plant.get("longest_streak", 0)), Colors.ACCENT_ORANGE),
            ("Total", str(plant.get("total_waterings", 0)), Colors.ACCENT_BLUE),
        ]
        for i, (lbl, val, col) in enumerate(stats):
            stats_frame.grid_columnconfigure(i, weight=1)
            f = ctk.CTkFrame(stats_frame, fg_color=Colors.BG_CARD, corner_radius=Radius.SM)
            f.grid(row=0, column=i, sticky="ew", padx=3, pady=2)
            ctk.CTkLabel(f, text=val, font=(Fonts.FAMILY, 18, "bold"),
                         text_color=col).pack(padx=Spacing.SM, pady=(Spacing.XS, 0))
            ctk.CTkLabel(f, text=lbl, font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
                         text_color=Colors.TEXT_MUTED).pack(padx=Spacing.SM, pady=(0, Spacing.XS))

        facts = ctk.CTkFrame(
            content,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.MD,
            border_width=1,
            border_color=Colors.BORDER,
        )
        facts.pack(fill="x", pady=(0, Spacing.XS))
        facts.grid_columnconfigure((0, 1), weight=1)

        freq_h = int(plant.get("water_freq_hours", 24) or 24)
        left_lines = [
            ("Season", plant.get("season") or "N/A"),
            ("Soil Needed", plant.get("soil_type") or "N/A"),
            ("Water Needed", plant.get("water_need") or "medium"),
            ("Watering", f"Every {freq_h}h"),
        ]
        right_lines = [
            ("Planted On", plant.get("planted_on", "N/A")[:10] if plant.get("planted_on") else "N/A"),
            ("Description", plant.get("description") or plant.get("notes") or "No description added."),
        ]

        left_col = ctk.CTkFrame(facts, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(Spacing.MD, Spacing.SM), pady=Spacing.MD)
        right_col = ctk.CTkFrame(facts, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(Spacing.SM, Spacing.MD), pady=Spacing.MD)

        for k, v in left_lines:
            ctk.CTkLabel(
                left_col,
                text=f"{k}: {v}",
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                text_color=Colors.TEXT_LIGHT,
                anchor="w",
            ).pack(anchor="w", pady=1)

        for i, (k, v) in enumerate(right_lines):
            ctk.CTkLabel(
                right_col,
                text=k,
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).pack(anchor="w", pady=(0 if i == 0 else Spacing.XS, 0))
            ctk.CTkLabel(
                right_col,
                text=str(v),
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                text_color=Colors.TEXT_LIGHT,
                anchor="w",
                justify="left",
                wraplength=360,
            ).pack(anchor="w", pady=(2, 0))

        history_row = ctk.CTkFrame(content, fg_color="transparent")
        history_row.pack(fill="x", pady=(0, Spacing.XS))
        history_row.grid_columnconfigure((0, 1), weight=1)
        history_row.grid_rowconfigure(0, weight=1)

        water_col = ctk.CTkFrame(history_row, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
        water_col.grid(row=0, column=0, sticky="nsew", padx=(0, Spacing.SM))
        ctk.CTkLabel(
            water_col,
            text="Watering History",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.ACCENT_BLUE,
            anchor="w",
        ).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        history_frame = ctk.CTkScrollableFrame(water_col, fg_color="transparent", corner_radius=0, height=180)
        history_frame.pack(fill="both", expand=True, padx=Spacing.SM, pady=(0, Spacing.SM))

        history = db.get_watering_history(self._plant_id, limit=15)
        if not history:
            ctk.CTkLabel(history_frame, text="No watering records yet.",
                         font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                         text_color=Colors.TEXT_MUTED).pack(padx=Spacing.SM, pady=Spacing.SM)
        else:
            for entry in history:
                on_time = entry.get("on_time", 1)
                color = Colors.TEXT_SUCCESS if on_time else Colors.TEXT_WARNING
                icon = "OK" if on_time else "LATE"
                try:
                    dt = datetime.fromisoformat(entry["watered_at"])
                    ts = dt.strftime("%b %d, %H:%M")
                except ValueError:
                    ts = entry["watered_at"]
                ctk.CTkLabel(history_frame, text=f"  [{icon}]  {ts}",
                             font=(Fonts.FAMILY_MONO, Fonts.SIZE_SMALL),
                             text_color=color, anchor="w").pack(anchor="w", padx=Spacing.SM, pady=1)

        check_col = ctk.CTkFrame(history_row, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
        check_col.grid(row=0, column=1, sticky="nsew", padx=(Spacing.SM, 0))
        ctk.CTkLabel(
            check_col,
            text="Weekly Check-ins",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.ACCENT_ORANGE,
            anchor="w",
        ).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        checkin_frame = ctk.CTkScrollableFrame(check_col, fg_color="transparent", corner_radius=0, height=180)
        checkin_frame.pack(fill="both", expand=True, padx=Spacing.SM, pady=(0, Spacing.SM))

        checkins = db.get_checkins(self._plant_id)
        if not checkins:
            ctk.CTkLabel(checkin_frame, text="No check-ins yet. Use the Check-in button!",
                         font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                         text_color=Colors.TEXT_MUTED).pack(padx=Spacing.SM, pady=Spacing.SM)
        else:
            for ci in checkins[:10]:
                row_wrap = ctk.CTkFrame(checkin_frame, fg_color="transparent")
                row_wrap.pack(fill="x", padx=Spacing.SM, pady=(0, Spacing.XS), anchor="w")

                try:
                    dt = datetime.fromisoformat(ci["week_date"])
                    ts = dt.strftime("%b %d")
                except ValueError:
                    ts = ci["week_date"]
                flower = "  [Flowering]" if ci.get("flowering") else ""
                text = f"  {ts}: {ci.get('height_cm', 0)}cm, +{ci.get('new_leaves', 0)} leaves{flower}"
                if ci.get("note"):
                    text += f"   {ci['note']}"
                ctk.CTkLabel(row_wrap, text=text,
                             font=(Fonts.FAMILY_MONO, Fonts.SIZE_SMALL),
                             text_color=Colors.TEXT_LIGHT, anchor="w", justify="left", wraplength=360).pack(anchor="w", pady=(0, 2))

                img_path = str(ci.get("image_path") or "").strip()
                if img_path:
                    abs_path = img_path if os.path.isabs(img_path) else os.path.join(os.path.dirname(__file__), img_path)
                    if os.path.exists(abs_path):
                        try:
                            with Image.open(abs_path) as img:
                                pil = img.convert("RGBA")
                                pil.thumbnail((120, 90), Image.Resampling.LANCZOS)
                            ctk_img = CTkImage(pil, size=pil.size)
                            img_lbl = ctk.CTkLabel(row_wrap, text="", image=ctk_img)
                            img_lbl.pack(anchor="w", pady=(0, 2))
                            img_lbl._img_ref = ctk_img
                        except Exception:
                            pass

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=pad, pady=(Spacing.XS, Spacing.SM))
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btn_frame, text="Weekly Check-in", height=34,
            fg_color=Colors.ACCENT_ORANGE, hover_color=Colors.EARTH_LIGHT,
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._open_checkin,
        ).grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS), pady=(0, Spacing.XS))

        ctk.CTkButton(
            btn_frame, text="Edit Plant", height=32,
            fg_color=Colors.ACCENT_BLUE, hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._edit,
        ).grid(row=0, column=1, sticky="ew", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkButton(
            btn_frame, text="Remove", height=32,
            fg_color=Colors.TEXT_DANGER, hover_color="#E53935",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._remove,
        ).grid(row=0, column=2, sticky="ew", padx=(Spacing.XS, 0), pady=(0, Spacing.XS))

        ctk.CTkButton(
            btn_frame, text="Close", height=32,
            fg_color=Colors.BG_INPUT, hover_color=Colors.BORDER,
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY),
            command=self.destroy,
        ).grid(row=1, column=2, sticky="ew", padx=(Spacing.XS, 0), pady=(Spacing.XS, 0))

    # Handle back to dashboard
    def _back_to_dashboard(self) -> None:
        if self._on_back_to_dashboard:
            self._on_back_to_dashboard()
        self.destroy()

    # Open checkin
    def _open_checkin(self) -> None:
        plant = db.get_plant(self._plant_id)
        if not plant:
            return
        dialog = _CheckinDialog(self, plant)
        self.wait_window(dialog)
        self._build_ui()

    # Remove the current data
    def _remove(self) -> None:
        plant = db.get_plant(self._plant_id)
        if not plant:
            return
        dialog = _ConfirmDeleteDialog(self, plant)
        self.wait_window(dialog)
        if getattr(dialog, "confirmed", False):
            db.delete_plant(self._plant_id)
            db.add_message(f"'{plant['name']}' removed from garden.", "Garden", "warning")
            self._deleted = True
            self.destroy()

    # Handle water
    def _water(self) -> None:
        db.mark_watered(self._plant_id)
        self._build_ui()

    # Handel change status
    def _change_status(self) -> None:
        dialog = _StatusDialog(self, db.get_plant(self._plant_id))
        self.wait_window(dialog)
        self._build_ui()

    # Handle edit
    def _edit(self) -> None:
        dialog = _EditPlantDialog(self, db.get_plant(self._plant_id))
        self.wait_window(dialog)
        self._build_ui()



class _EditPlantDialog(_FloatingModal):
    # Set up this object and prepare its initial state
    def __init__(self, parent, plant: dict):
        super().__init__(parent, width=520, height=720, title=f"Edit: {plant['name']}")
        self._plant = plant
        self._image_preview_ref: Optional[CTkImage] = None
        self._image_path_var = ctk.StringVar(value=str(plant.get("image_path") or ""))

        pad = Spacing.LG

        ctk.CTkLabel(
            self,
            text="Edit Plant",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.PRIMARY_DARK,
        ).pack(pady=(pad, 2))
        ctk.CTkLabel(
            self,
            text="Update details, schedule, and your real plant photo",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
            text_color=Colors.TEXT_MUTED,
        ).pack(pady=(0, Spacing.SM))

        body = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=pad, pady=(0, Spacing.SM))
        body.grid_columnconfigure(0, weight=1)

        basic_card = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=Radius.MD, border_width=1, border_color=Colors.BORDER)
        basic_card.pack(fill="x", pady=(0, Spacing.SM))
        self._section_title(basic_card, "Basic Details")

        self._name = self._field(basic_card, "Name", plant["name"])
        self._nepali = self._field(basic_card, "Nepali Name", plant.get("name_nepali", ""))
        self._notes = self._field(basic_card, "Notes", plant.get("notes", ""))

        schedule_card = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=Radius.MD, border_width=1, border_color=Colors.BORDER)
        schedule_card.pack(fill="x", pady=(0, Spacing.SM))
        self._section_title(schedule_card, "Watering")

        ctk.CTkLabel(schedule_card, text="Watering Frequency (hours)",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=Spacing.MD)
        self._freq = ctk.CTkEntry(schedule_card, fg_color=Colors.BG_INPUT,
                                   border_color=Colors.BORDER, corner_radius=Radius.SM)
        self._freq.insert(0, str(int(plant.get("water_freq_hours", 24))))
        self._freq.pack(fill="x", padx=Spacing.MD, pady=(2, Spacing.SM))

        ctk.CTkLabel(schedule_card, text="Water Need",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=Spacing.MD)
        self._water_need = ctk.CTkOptionMenu(
            schedule_card, values=["low", "medium", "high"],
            fg_color=Colors.BG_INPUT, button_color=Colors.PRIMARY,
            button_hover_color=Colors.PRIMARY_HOVER, corner_radius=Radius.SM,
            text_color="black",
        )
        self._water_need.set(plant.get("water_need", "medium"))
        self._water_need.pack(fill="x", padx=Spacing.MD, pady=(2, Spacing.SM))

        date_card = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=Radius.MD, border_width=1, border_color=Colors.BORDER)
        date_card.pack(fill="x", pady=(0, Spacing.SM))
        self._section_title(date_card, "Planting Date")

        ctk.CTkLabel(
            date_card,
            text="Planted Date",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=Spacing.MD)

        planted_row = ctk.CTkFrame(date_card, fg_color="transparent")
        planted_row.pack(fill="x", padx=Spacing.MD, pady=(2, Spacing.SM))
        planted_row.grid_columnconfigure(0, weight=1)

        planted_raw = str(plant.get("planted_on") or "").strip()
        planted_date = planted_raw[:10] if planted_raw else datetime.now().strftime("%Y-%m-%d")
        self._planted_on_var = ctk.StringVar(value=planted_date)

        self._planted_entry = ctk.CTkEntry(
            planted_row,
            textvariable=self._planted_on_var,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
        )
        self._planted_entry.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        ctk.CTkButton(
            planted_row,
            text="Calendar",
            width=100,
            fg_color=Colors.ACCENT_BLUE,
            hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            command=self._pick_planted_date,
        ).grid(row=0, column=1, sticky="e")

        image_card = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=Radius.MD, border_width=1, border_color=Colors.BORDER)
        image_card.pack(fill="x", pady=(0, Spacing.SM))
        self._section_title(image_card, "Plant Image")

        img_row = ctk.CTkFrame(image_card, fg_color="transparent")
        img_row.pack(fill="x", padx=Spacing.MD, pady=(2, Spacing.XS))
        img_row.grid_columnconfigure(0, weight=1)

        self._image_entry = ctk.CTkEntry(
            img_row,
            textvariable=self._image_path_var,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
        )
        self._image_entry.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        ctk.CTkButton(
            img_row,
            text="Upload File",
            width=110,
            fg_color=Colors.ACCENT_BLUE,
            hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            command=self._upload_image,
        ).grid(row=0, column=1, sticky="e", padx=(0, Spacing.XS))

        ctk.CTkButton(
            img_row,
            text="Take Photo",
            width=100,
            fg_color=Colors.ACCENT_ORANGE,
            hover_color=Colors.EARTH_LIGHT,
            corner_radius=Radius.SM,
            command=self._take_photo,
        ).grid(row=0, column=2, sticky="e")

        preview_row = ctk.CTkFrame(image_card, fg_color="transparent")
        preview_row.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.SM))

        self._image_preview = ctk.CTkLabel(
            preview_row,
            text="No image selected",
            width=120,
            height=96,
            fg_color=Colors.BG_INPUT,
            corner_radius=Radius.SM,
            text_color=Colors.TEXT_MUTED,
        )
        self._image_preview.pack(anchor="w")

        ctk.CTkButton(
            preview_row,
            text="Clear Image",
            width=100,
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=self._clear_image,
        ).pack(anchor="w", pady=(Spacing.XS, 0))

        self._refresh_image_preview()

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=pad, pady=(0, Spacing.MD))
        actions.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            actions,
            text="Cancel",
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=self.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        ctk.CTkButton(
            actions, text="Save Changes", fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER, corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._save,
        ).grid(row=0, column=1, sticky="ew", padx=(Spacing.XS, 0))

    # Handle section title
    def _section_title(self, parent: ctk.CTkFrame, text: str) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            text_color=Colors.ACCENT_BLUE,
            anchor="w",
        ).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

    # Copy image to store
    def _copy_image_to_store(self, src_path: str) -> str:
        base_dir = os.path.dirname(__file__)
        store_dir = os.path.join(base_dir, "uploads", "plants")
        os.makedirs(store_dir, exist_ok=True)
        ext = os.path.splitext(src_path)[1].lower() or ".jpg"
        name = f"plant_{self._plant['id']}_{uuid.uuid4().hex[:10]}{ext}"
        target = os.path.join(store_dir, name)
        shutil.copy2(src_path, target)
        return os.path.relpath(target, base_dir)

    # Handle upload image
    def _upload_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Plant Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            saved = self._copy_image_to_store(path)
            self._image_path_var.set(saved)
            self._refresh_image_preview()
        except Exception:
            return

    # Handle take photo
    def _take_photo(self) -> None:
        try:
            import cv2  # type: ignore
        except Exception:
            self._upload_image()
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release()
            self._upload_image()
            return

        captured_path = ""
        window = "Take Photo (SPACE: capture, ESC: cancel)"
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                cv2.imshow(window, frame)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    break
                if key == 32:  # SPACE
                    base_dir = os.path.dirname(__file__)
                    store_dir = os.path.join(base_dir, "uploads", "plants")
                    os.makedirs(store_dir, exist_ok=True)
                    filename = f"plant_{self._plant['id']}_{uuid.uuid4().hex[:10]}.jpg"
                    captured_path = os.path.join(store_dir, filename)
                    cv2.imwrite(captured_path, frame)
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

        if captured_path:
            self._image_path_var.set(os.path.relpath(captured_path, os.path.dirname(__file__)))
            self._refresh_image_preview()

    # Clear image
    def _clear_image(self) -> None:
        self._image_path_var.set("")
        self._refresh_image_preview()

    # Refresh image preview
    def _refresh_image_preview(self) -> None:
        path = (self._image_path_var.get() or "").strip()
        if not path:
            self._image_preview_ref = None
            self._image_preview.configure(image=None, text="No image selected")
            return

        abs_path = path if os.path.isabs(path) else os.path.join(os.path.dirname(__file__), path)
        if not os.path.exists(abs_path):
            self._image_preview_ref = None
            self._image_preview.configure(image=None, text="Image not found")
            return

        try:
            with Image.open(abs_path) as img:
                pil = img.convert("RGBA")
                pil.thumbnail((120, 96), Image.Resampling.LANCZOS)
            self._image_preview_ref = CTkImage(pil, size=pil.size)
            self._image_preview.configure(image=self._image_preview_ref, text="")
        except Exception:
            self._image_preview_ref = None
            self._image_preview.configure(image=None, text="Invalid image")

    # Pick planted date
    def _pick_planted_date(self) -> None:
        picker = _CalendarDatePicker(self, initial_date=self._planted_on_var.get().strip())
        self.wait_window(picker)
        if getattr(picker, "selected_date", None):
            self._planted_on_var.set(picker.selected_date)

    # Handle field
    def _field(self, parent: ctk.CTkFrame, label: str, value: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label,
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=Spacing.MD)
        entry = ctk.CTkEntry(parent, fg_color=Colors.BG_INPUT,
                              border_color=Colors.BORDER, corner_radius=Radius.SM)
        entry.insert(0, value)
        entry.pack(fill="x", padx=Spacing.MD, pady=(2, Spacing.SM))
        return entry

    # Save the current data
    def _save(self) -> None:
        name = self._name.get().strip()
        if not name:
            return
        try:
            freq = max(1, int(self._freq.get()))
        except ValueError:
            freq = 24

        planted_date = (self._planted_on_var.get() or "").strip()
        try:
            planted_date = datetime.strptime(planted_date, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            planted_date = (str(self._plant.get("planted_on") or "")[:10]) or datetime.now().strftime("%Y-%m-%d")

        db.update_plant(
            self._plant["id"],
            name=name,
            name_nepali=self._nepali.get().strip(),
            water_freq_hours=freq,
            water_need=self._water_need.get(),
            notes=self._notes.get().strip(),
            planted_on=planted_date,
            image_path=(self._image_path_var.get() or "").strip(),
        )
        self.destroy()


class _CalendarDatePicker(_FloatingModal):
    """Simple in-app calendar picker that returns YYYY-MM-DD."""

    WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    # Set up this object and prepare its initial state
    def __init__(self, parent, initial_date: str = ""):
        super().__init__(parent, width=360, height=380, title="Select Date")
        self.configure(fg_color="#F2F5F9")

        self.selected_date: str | None = None

        try:
            dt = datetime.strptime((initial_date or "").strip()[:10], "%Y-%m-%d")
        except ValueError:
            dt = datetime.now()

        self._year = dt.year
        self._month = dt.month
        self._initial_year = dt.year
        self._initial_month = dt.month
        self._initial_day = dt.day

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        nav = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=Radius.MD, border_width=1, border_color="#DDE3EA")
        nav.grid(row=0, column=0, sticky="ew", padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))
        nav.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            nav,
            text="<",
            width=34,
            fg_color="#EAF0F7",
            hover_color="#DCE8F5",
            text_color="#111111",
            command=lambda: self._shift_month(-1),
        ).grid(row=0, column=0, sticky="w", padx=Spacing.SM, pady=Spacing.SM)

        self._title = ctk.CTkLabel(
            nav,
            text="",
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            text_color="#111111",
        )
        self._title.grid(row=0, column=1)

        ctk.CTkButton(
            nav,
            text=">",
            width=34,
            fg_color="#EAF0F7",
            hover_color="#DCE8F5",
            text_color="#111111",
            command=lambda: self._shift_month(1),
        ).grid(row=0, column=2, sticky="e", padx=Spacing.SM, pady=Spacing.SM)

        weekdays = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=Radius.MD, border_width=1, border_color="#DDE3EA")
        weekdays.grid(row=1, column=0, sticky="ew", padx=Spacing.MD)
        for i, wd in enumerate(self.WEEKDAYS):
            ctk.CTkLabel(
                weekdays,
                text=wd,
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
                text_color="#111111",
                width=40,
            ).grid(row=0, column=i, padx=2, pady=(6, 6))

        self._days = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=Radius.MD, border_width=1, border_color="#DDE3EA")
        self._days.grid(row=2, column=0, sticky="nsew", padx=Spacing.MD, pady=(0, Spacing.SM))

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=3, column=0, sticky="ew", padx=Spacing.MD, pady=(0, Spacing.MD))
        foot.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            foot,
            text="Today",
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color="#111111",
            command=self._pick_today,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            foot,
            text="Cancel",
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color="#111111",
            command=self.destroy,
        ).grid(row=0, column=1, sticky="e")

        self._render_days()

    # Handle shift month
    def _shift_month(self, delta: int) -> None:
        m = self._month + delta
        y = self._year
        if m < 1:
            m = 12
            y -= 1
        elif m > 12:
            m = 1
            y += 1
        self._month = m
        self._year = y
        self._render_days()

    # Pick today
    def _pick_today(self) -> None:
        self.selected_date = datetime.now().strftime("%Y-%m-%d")
        self.destroy()

    # Pick day
    def _pick_day(self, day: int) -> None:
        self.selected_date = f"{self._year:04d}-{self._month:02d}-{day:02d}"
        self.destroy()

    # Render days
    def _render_days(self) -> None:
        for w in self._days.winfo_children():
            w.destroy()

        self._title.configure(text=f"{calendar.month_name[self._month]} {self._year}")

        for c in range(7):
            self._days.grid_columnconfigure(c, weight=1)

        first_weekday, month_days = calendar.monthrange(self._year, self._month)
        col = first_weekday
        row = 0
        today = datetime.now()
        day_palette = [
            "#EEF6FF",  # Mon
            "#F2EEFF",  # Tue
            "#EEFBF3",  # Wed
            "#FFF5E9",  # Thu
            "#FDEFF4",  # Fri
            "#FFF9E1",  # Sat
            "#EAF8F8",  # Sun
        ]

        for day in range(1, month_days + 1):
            is_today = (day == today.day and self._month == today.month and self._year == today.year)
            is_initial = (
                day == self._initial_day
                and self._month == self._initial_month
                and self._year == self._initial_year
            )

            if is_today:
                fg = "#FFDFA3"
                hover = "#FFD287"
            elif is_initial:
                fg = "#C7F0D8"
                hover = "#AFE8C8"
            else:
                fg = day_palette[col]
                hover = "#DCE8F5"

            btn = ctk.CTkButton(
                self._days,
                text=str(day),
                width=42,
                height=32,
                corner_radius=Radius.SM,
                fg_color=fg,
                hover_color=hover,
                text_color="#111111",
                command=lambda d=day: self._pick_day(d),
            )
            btn.grid(row=row, column=col, padx=2, pady=2)

            col += 1
            if col > 6:
                col = 0
                row += 1



class _ConfirmDeleteDialog(_FloatingModal):
    # Set up this object and prepare its initial state
    def __init__(self, parent, plant: dict):
        super().__init__(parent, width=400, height=230, title="Confirm Delete")
        self.confirmed = False

        ctk.CTkLabel(
            self, text=f"Remove '{plant['name']}' from garden?",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.TEXT_LIGHT,
        ).pack(pady=(Spacing.XL, Spacing.SM))

        ctk.CTkLabel(
            self, text="This will delete all watering history and check-ins.\nThis cannot be undone.",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_WARNING,
        ).pack(pady=Spacing.SM)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=Spacing.MD)

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=self.destroy,
        ).pack(side="left", padx=Spacing.SM)

        ctk.CTkButton(
            btn_frame, text="Delete", width=100,
            fg_color=Colors.TEXT_DANGER, hover_color="#E53935",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._confirm,
        ).pack(side="left")

    # Handle confirm
    def _confirm(self) -> None:
        self.confirmed = True
        self.destroy()



class _CheckinDialog(_FloatingModal):
    # Set up this object and prepare its initial state
    def __init__(self, parent, plant: dict):
        super().__init__(parent, width=520, height=620, title=f"Check-in: {plant['name']}")
        self._plant = plant
        self._image_preview_ref: Optional[CTkImage] = None
        self._image_path_var = ctk.StringVar(value="")

        pad = Spacing.LG

        ctk.CTkLabel(
            self,
            text=f"Weekly Check-in: {plant['name']}",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.PRIMARY_DARK,
        ).pack(pady=(pad, 2))
        ctk.CTkLabel(
            self,
            text="Capture this week\'s growth progress",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
            text_color=Colors.TEXT_MUTED,
        ).pack(pady=(0, Spacing.SM))

        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Radius.MD, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="both", expand=True, padx=pad, pady=(0, Spacing.SM))
        card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(card, text="Height (cm)",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.MD, 4))
        self._height = ctk.CTkEntry(card, fg_color=Colors.BG_INPUT,
                                     border_color=Colors.BORDER, corner_radius=Radius.SM,
                                     placeholder_text="e.g. 15.5")
        self._height.grid(row=1, column=0, sticky="ew", padx=Spacing.MD, pady=(0, Spacing.SM))

        ctk.CTkLabel(card, text="New Leaves",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).grid(row=0, column=1, sticky="w", padx=(0, Spacing.MD), pady=(Spacing.MD, 4))
        self._leaves = ctk.CTkEntry(card, fg_color=Colors.BG_INPUT,
                                     border_color=Colors.BORDER, corner_radius=Radius.SM,
                                     placeholder_text="e.g. 3")
        self._leaves.grid(row=1, column=1, sticky="ew", padx=(0, Spacing.MD), pady=(0, Spacing.SM))

        self._flowering = ctk.CTkCheckBox(
            card, text="Flowering this week",
            font=(Fonts.FAMILY, Fonts.SIZE_BODY),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            border_color=Colors.BORDER, text_color=Colors.TEXT_LIGHT,
        )
        self._flowering.grid(row=2, column=0, columnspan=2, sticky="w", padx=Spacing.MD, pady=(0, Spacing.SM))

        ctk.CTkLabel(card, text="Notes",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).grid(row=3, column=0, columnspan=2, sticky="w", padx=Spacing.MD, pady=(0, 4))
        self._note = ctk.CTkTextbox(card, fg_color=Colors.BG_INPUT,
                                     border_color=Colors.BORDER, border_width=1,
                                     corner_radius=Radius.SM, height=110)
        self._note.grid(row=4, column=0, columnspan=2, sticky="ew", padx=Spacing.MD, pady=(0, Spacing.MD))

        ctk.CTkLabel(card, text="Weekly Photo",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).grid(row=5, column=0, columnspan=2, sticky="w", padx=Spacing.MD, pady=(0, 4))

        img_row = ctk.CTkFrame(card, fg_color="transparent")
        img_row.grid(row=6, column=0, columnspan=2, sticky="ew", padx=Spacing.MD, pady=(0, Spacing.XS))
        img_row.grid_columnconfigure(0, weight=1)

        self._image_entry = ctk.CTkEntry(
            img_row,
            textvariable=self._image_path_var,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
            placeholder_text="No image selected",
        )
        self._image_entry.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        ctk.CTkButton(
            img_row,
            text="Upload File",
            width=110,
            fg_color=Colors.ACCENT_BLUE,
            hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            command=self._upload_image,
        ).grid(row=0, column=1, sticky="e", padx=(0, Spacing.XS))

        ctk.CTkButton(
            img_row,
            text="Take Photo",
            width=100,
            fg_color=Colors.ACCENT_ORANGE,
            hover_color=Colors.EARTH_LIGHT,
            corner_radius=Radius.SM,
            command=self._take_photo,
        ).grid(row=0, column=2, sticky="e")

        preview_row = ctk.CTkFrame(card, fg_color="transparent")
        preview_row.grid(row=7, column=0, columnspan=2, sticky="ew", padx=Spacing.MD, pady=(0, Spacing.MD))

        self._image_preview = ctk.CTkLabel(
            preview_row,
            text="No image selected",
            width=130,
            height=96,
            fg_color=Colors.BG_INPUT,
            corner_radius=Radius.SM,
            text_color=Colors.TEXT_MUTED,
        )
        self._image_preview.pack(anchor="w")

        ctk.CTkButton(
            preview_row,
            text="Clear Image",
            width=100,
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=self._clear_image,
        ).pack(anchor="w", pady=(Spacing.XS, 0))

        self._refresh_image_preview()

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=pad, pady=(0, Spacing.MD))
        actions.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            actions,
            text="Cancel",
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=self.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        ctk.CTkButton(
            actions, text="Save Check-in", fg_color=Colors.ACCENT_BLUE,
            hover_color="#5AB0F5", corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._save,
        ).grid(row=0, column=1, sticky="ew", padx=(Spacing.XS, 0))

    # Copy image to store
    def _copy_image_to_store(self, src_path: str) -> str:
        base_dir = os.path.dirname(__file__)
        store_dir = os.path.join(base_dir, "uploads", "checkins")
        os.makedirs(store_dir, exist_ok=True)
        ext = os.path.splitext(src_path)[1].lower() or ".jpg"
        name = f"checkin_{self._plant['id']}_{uuid.uuid4().hex[:10]}{ext}"
        target = os.path.join(store_dir, name)
        shutil.copy2(src_path, target)
        return os.path.relpath(target, base_dir)

    # HAndle upload image
    def _upload_image(self) -> None:
        path = filedialog.askopenfilename(
             title="Select Weekly Check-in Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            saved = self._copy_image_to_store(path)
            self._image_path_var.set(saved)
            self._refresh_image_preview()
        except Exception:
            return

    #  Takes photo from file
    def _take_photo(self) -> None:
        try:
            import cv2  # type: ignore
        except Exception:
            self._upload_image()
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release()
            self._upload_image()
            return

        captured_path = ""
        window = "Check-in Photo (SPACE: capture, ESC: cancel)"
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                cv2.imshow(window, frame)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    break
                if key == 32:
                    base_dir = os.path.dirname(__file__)
                    store_dir = os.path.join(base_dir, "uploads", "checkins")
                    os.makedirs(store_dir, exist_ok=True)
                    filename = f"checkin_{self._plant['id']}_{uuid.uuid4().hex[:10]}.jpg"
                    captured_path = os.path.join(store_dir, filename)
                    cv2.imwrite(captured_path, frame)
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

        if captured_path:
            self._image_path_var.set(os.path.relpath(captured_path, os.path.dirname(__file__)))
            self._refresh_image_preview()

    # Clear image
    def _clear_image(self) -> None:
        self._image_path_var.set("")
        self._refresh_image_preview()

    # Refresh image preview
    def _refresh_image_preview(self) -> None:
        path = (self._image_path_var.get() or "").strip()
        if not path:
            self._image_preview_ref = None
            self._image_preview.configure(image=None, text="No image selected")
            return

        abs_path = path if os.path.isabs(path) else os.path.join(os.path.dirname(__file__), path)
        if not os.path.exists(abs_path):
            self._image_preview_ref = None
            self._image_preview.configure(image=None, text="Image not found")
            return

        try:
            with Image.open(abs_path) as img:
                pil = img.convert("RGBA")
                pil.thumbnail((130, 96), Image.Resampling.LANCZOS)
            self._image_preview_ref = CTkImage(pil, size=pil.size)
            self._image_preview.configure(image=self._image_preview_ref, text="")
        except Exception:
            self._image_preview_ref = None
            self._image_preview.configure(image=None, text="Invalid image")

    # Save the current data
    def _save(self) -> None:
        try:
            h = float(self._height.get() or 0)
        except ValueError:
            h = 0.0
        try:
            lv = int(self._leaves.get() or 0)
        except ValueError:
            lv = 0
        db.add_checkin(
            plant_id=self._plant["id"],
            height_cm=h,
            new_leaves=lv,
            flowering=bool(self._flowering.get()),
            note=self._note.get("1.0", "end").strip(),
            image_path=(self._image_path_var.get() or "").strip(),
        )
        db.add_message(
            f"Check-in for '{self._plant['name']}': {h}cm, +{lv} leaves",
            "Garden", "info"
        )
        self.destroy()



class _StatusDialog(_FloatingModal):
    # Set up this object and prepar its initial state
    def __init__(self, parent, plant: dict):
        super().__init__(parent, width=360, height=260, title=f"Status: {plant['name']}")
        self._plant = plant

        pad = Spacing.LG

        ctk.CTkLabel(self, text=f"Status for {plant['name']}",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.PRIMARY_DARK).pack(pady=(pad, Spacing.MD))

        self._status = ctk.CTkOptionMenu(
            self, values=["healthy", "needs_water", "sick"],
            fg_color=Colors.BG_INPUT, button_color=Colors.PRIMARY,
            button_hover_color=Colors.PRIMARY_HOVER, corner_radius=Radius.SM,
            text_color="black",
        )
        self._status.set(plant["status"])
        self._status.pack(fill="x", padx=pad, pady=Spacing.SM)

        ctk.CTkButton(
            self, text="Update", fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER, corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._save,
        ).pack(pady=Spacing.LG)

    # Save the current data
    def _save(self) -> None:
        db.update_plant_status(self._plant["id"], self._status.get())
        self.destroy()
