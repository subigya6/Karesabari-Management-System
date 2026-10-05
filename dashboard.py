"""
dashboard.py  Water Notifier / Dashboard for Karesabari.

Features:
  - Summary stats row (total plants, overdue, total waterings)
  - Live countdown timers that update every second
  - Overdue alerts section
  - Watering schedule with "Water Now" buttons
  - Message relay with type-coloured bubbles
  - Auto-refresh polling every 30 s to update statuses
"""

from __future__ import annotations

import os
import customtkinter as ctk
from typing import Callable, Optional
from datetime import datetime, timedelta
from PIL import Image
from customtkinter import CTkImage

from theme import Colors, Fonts, Spacing, Radius
import database as db

class DashboardFrame(ctk.CTkFrame):
    """Main dashboard / water notifier view."""

    # Set up this object and prepare its initial state
    def __init__(self, master: ctk.CTkFrame, on_navigate: Optional[Callable] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_navigate = on_navigate
        self._timer_labels = []
        self._tick_id = None
        self._loading_messages = False
        self._pending_msg_refresh_id = None
        self._msg_poll_id = None
        self._last_seen_msg_id = None
        self._overdue_notified: set[int] = set()
        self._schedule_image_cache: dict[tuple[str, tuple[int, int]], CTkImage] = {}

        self.grid_columnconfigure(0, weight=5)  # middle content area
        self.grid_columnconfigure(1, weight=2)  # right notification panel (narrower)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkLabel(
            self,
            text="Dashboard",
            font=(Fonts.FAMILY, Fonts.SIZE_TITLE, "bold"),
            text_color=Colors.PRIMARY_DARK,
            anchor="w",
        )
        header.grid(row=0, column=0, columnspan=2, sticky="w",
                     padx=Spacing.LG, pady=(Spacing.LG, Spacing.XS))

        self._stats_frame = ctk.CTkFrame(
            self,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.LG,
        )
        self._stats_frame.grid(row=1, column=0, columnspan=2, sticky="ew",
                                padx=Spacing.LG, pady=(0, Spacing.SM))

        left_wrap = ctk.CTkFrame(self, fg_color="transparent")
        left_wrap.grid(row=2, column=0, sticky="nsew", padx=(Spacing.LG, Spacing.SM), pady=Spacing.SM)
        left_wrap.grid_rowconfigure(1, weight=1)
        left_wrap.grid_columnconfigure(0, weight=1)

        header_row = ctk.CTkFrame(left_wrap, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, Spacing.SM))
        header_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_row,
            text="MY GARDEN",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.ACCENT_ORANGE,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._add_menu_open = False
        self._add_menu = ctk.CTkFrame(header_row, fg_color="transparent")
        self._add_menu.grid(row=0, column=1, sticky="e")

        self._add_btn = ctk.CTkButton(
            self._add_menu,
            text="Add Plant",
            height=32,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            command=self._toggle_add_menu,
        )
        self._add_btn.grid(row=0, column=0, sticky="e")

        self._add_from_cat_btn = ctk.CTkButton(
            self._add_menu,
            text="From Catalogue",
            height=30,
            fg_color=Colors.ACCENT_BLUE,
            hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=self._open_catalogue_add,
        )
        self._add_custom_btn = ctk.CTkButton(
            self._add_menu,
            text="Custom Plant",
            height=30,
            fg_color=Colors.ACCENT_YELLOW,          # <-- changed
            hover_color=Colors.ACCENT_YELLOW,       # <-- keep consistent (can be tweaked later)
            text_color=Colors.TEXT_DARK,            # <-- better contrast on yellow
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=self._open_custom_add,
        )

        self._add_from_cat_btn.grid_remove()
        self._add_custom_btn.grid_remove()

        self._schedule_frame = ctk.CTkScrollableFrame(
            left_wrap,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.LG,
        )
        self._schedule_frame.grid(row=1, column=0, sticky="nsew")
        self._schedule_frame.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=2, column=1, sticky="nsew",
                    padx=(Spacing.SM, Spacing.LG), pady=Spacing.SM)
        right.grid_propagate(False)
        right.configure(width=320)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        notif_header = ctk.CTkFrame(right, fg_color="transparent")
        notif_header.grid(row=0, column=0, sticky="ew",
                          padx=(Spacing.XS, 0), pady=(0, Spacing.SM))
        notif_header.grid_columnconfigure(0, weight=1)

        msg_label = ctk.CTkLabel(
            notif_header, text="Notification Panel",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.ACCENT_ORANGE,
        )
        msg_label.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            notif_header,
            text="Refresh",
            width=90,
            height=30,
            fg_color="#DCFCE7",
            hover_color="#BBF7D0",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=self._refresh_notifications,
        ).grid(row=0, column=1, sticky="e")

        self._messages_frame = ctk.CTkScrollableFrame(
            right,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.LG,
        )
        self._messages_frame.grid(row=1, column=0, sticky="nsew",
                                  padx=0, pady=(0, Spacing.SM))
        self._messages_frame.grid_columnconfigure(0, weight=1)

        input_frame = ctk.CTkFrame(right, fg_color="transparent")
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        sep = ctk.CTkFrame(input_frame, fg_color=Colors.BORDER, height=1)
        sep.grid(row=0, column=0, columnspan=2, sticky="ew",
                 pady=(0, Spacing.XS))

        self._msg_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Send a note or water request...",
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
            height=36,
        )
        self._msg_entry.grid(row=1, column=0, sticky="ew",
                             padx=(0, Spacing.SM), pady=(Spacing.XS, 0))
        self._msg_entry.bind("<Return>", lambda e: self._send_message())

        send_btn = ctk.CTkButton(
            input_frame, text="Send", width=70,
            fg_color=Colors.ACCENT_ORANGE,
            hover_color=Colors.EARTH_LIGHT,
            corner_radius=Radius.SM,
            command=self._send_message,
        )
        send_btn.grid(row=1, column=1, pady=(Spacing.XS, 0))

        self.refresh()


    # Refresh the current data
    def refresh(self) -> None:
        db.auto_update_statuses()
        self._build_stats()
        self._load_schedule()

        overdue = db.get_overdue_plants()
        if overdue:
            garden_id = db.get_current_garden_id() if hasattr(db, "get_current_garden_id") else None
            current_overdue_ids = {
                int(p.get("id")) for p in overdue if p.get("id") is not None
            }
            self._overdue_notified.intersection_update(current_overdue_ids)
            for p in overdue:
                pid = p.get("id")
                if isinstance(pid, int) and pid in self._overdue_notified:
                    continue
                display_name = p['name']
                if p.get('name_nepali'):
                    display_name += f" ({p['name_nepali']})"

                db.add_message(
                    f"Watering required: {display_name} is overdue!",
                    sender="Garden Bot",
                    msg_type="warning",
                    garden_id=garden_id,
                )
                if isinstance(pid, int):
                    self._overdue_notified.add(pid)

        self._load_messages()
        self._ensure_message_poll()
        self._start_tick()

    # Build stats for this screen
    def _build_stats(self) -> None:
        for w in self._stats_frame.winfo_children():
            w.destroy()

        plants = db.get_all_plants()
        overdue = db.get_overdue_plants()

        total = len(plants)
        overdue_count = len(overdue)
        best_streak = max((p.get("streak", 0) for p in plants), default=0)
        total_waterings = sum(p.get("total_waterings", 0) for p in plants)

        stats = [
            ("Total Plants", str(total), Colors.PRIMARY),
            ("Overdue", str(overdue_count), Colors.TEXT_DANGER if overdue_count else Colors.TEXT_SUCCESS),
            ("Waterings", str(total_waterings), Colors.ACCENT_BLUE),
        ]

        for i, (label, value, color) in enumerate(stats):
            self._stats_frame.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(self._stats_frame, fg_color=Colors.BG_CARD,
                                corner_radius=Radius.MD, height=70)
            card.grid(row=0, column=i, sticky="ew", padx=Spacing.XS, pady=Spacing.XS)
            card.grid_propagate(False)
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure((0, 1), weight=1)

            ctk.CTkLabel(
                card, text=value,
                font=(Fonts.FAMILY, 22, "bold"),
                text_color=color,
            ).grid(row=0, column=0, sticky="s", padx=Spacing.SM)

            ctk.CTkLabel(
                card, text=label,
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
                text_color=Colors.TEXT_MUTED,
            ).grid(row=1, column=0, sticky="n", padx=Spacing.SM)

    # Load schedule into this view
    def _load_schedule(self) -> None:
        for w in self._schedule_frame.winfo_children():
            w.destroy()
        self._timer_labels.clear()

        plants = db.get_all_plants()

        if not plants:
            empty = ctk.CTkLabel(
                self._schedule_frame,
                text="No plants yet. Use Add Plant or browse the Catalogue!",
                font=(Fonts.FAMILY, Fonts.SIZE_BODY),
                text_color=Colors.TEXT_MUTED,
            )
            empty.grid(row=0, column=0, pady=Spacing.XL)
            return

        # Handle sort key
        def sort_key(p):
            nw = p.get("next_water_at", "")
            return (0 if self._is_overdue(p) else 1, nw or "9999")

        plants.sort(key=sort_key)

        seen_counts: dict[str, int] = {}
        for i, plant in enumerate(plants):
            key = str(plant.get("name") or "").strip().lower()
            seen_counts[key] = seen_counts.get(key, 0) + 1
            self._create_schedule_card(i, plant, instance_no=seen_counts[key])

    # Handle resolve schedule image path
    def _resolve_schedule_image_path(self, plant: dict) -> Optional[str]:
        explicit = str((plant or {}).get("image_path") or "").strip()
        if explicit:
            if os.path.isabs(explicit) and os.path.exists(explicit):
                return explicit
            base_dir = os.path.dirname(__file__)
            rel = os.path.join(base_dir, explicit.replace("\\", os.sep).replace("/", os.sep))
            if os.path.exists(rel):
                return rel

        base_dir = os.path.dirname(__file__)
        logo_dir = os.path.join(base_dir, "logo")

        slug_source = (plant or {}).get("slug") or (plant or {}).get("name", "")
        slug = slug_source.strip().lower().replace(" ", "_") if slug_source else ""
        if slug:
            for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                slug_path = os.path.join(logo_dir, f"{slug}{ext}")
                if os.path.exists(slug_path):
                    return slug_path

        try:
            name = str((plant or {}).get("name") or "").strip()
            if name:
                items = db.search_catalogue(name)
                for item in items:
                    if str(item.get("name") or "").strip().lower() == name.lower():
                        cat_path = str(item.get("image_path") or "").strip()
                        if not cat_path:
                            continue
                        if os.path.isabs(cat_path) and os.path.exists(cat_path):
                            return cat_path
                        rel = os.path.join(base_dir, cat_path.replace("\\", os.sep).replace("/", os.sep))
                        if os.path.exists(rel):
                            return rel
        except Exception:
            pass

        generic = os.path.join(logo_dir, "logo.png")
        if os.path.exists(generic):
            return generic
        return None

    # Return schedule image
    def _get_schedule_image(self, path: str, size: tuple[int, int]) -> Optional[CTkImage]:
        if not path:
            return None
        key = (path, size)
        if key in self._schedule_image_cache:
            return self._schedule_image_cache[key]
        try:
            img = Image.open(path)
        except (FileNotFoundError, OSError):
            return None
        ctk_img = CTkImage(img, size=size)
        self._schedule_image_cache[key] = ctk_img
        return ctk_img

    # Create schedule card
    def _create_schedule_card(self, row: int, plant: dict, instance_no: int = 1) -> None:
        is_overdue = self._is_overdue(plant)

        card = ctk.CTkFrame(
            self._schedule_frame,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.LG,
            border_width=2 if is_overdue else 1,
            border_color=Colors.TEXT_DANGER if is_overdue else Colors.BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", pady=Spacing.XS, padx=Spacing.XS)
        card.grid_columnconfigure(0, weight=1)

        self._bind_double_click(card, plant_id=plant["id"])

        ctk.CTkLabel(
            card,
            text=f"{(plant.get('name') or '').strip()} ({max(1, int(instance_no))})",
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            text_color=Colors.TEXT_LIGHT,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.SM, 0))

        nep = (plant.get("name_nepali") or "").strip()
        if nep:
            nep_lbl = ctk.CTkLabel(
                card,
                text=nep,
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                text_color=Colors.TEXT_SECONDARY,
                anchor="w",
            )
            nep_lbl.grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=(2, 0))
            self._bind_double_click(nep_lbl, plant_id=plant["id"])

        sci = (plant.get("scientific_name") or "").strip() or "Not specified"
        sci_lbl = ctk.CTkLabel(
            card,
            text=f"Scientific: {sci}",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "italic"),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        sci_lbl.grid(row=2, column=0, sticky="w", padx=Spacing.MD, pady=(2, 0))
        self._bind_double_click(sci_lbl, plant_id=plant["id"])

        countdown_lbl = ctk.CTkLabel(
            card,
            text="...",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        countdown_lbl.grid(row=3, column=0, sticky="w", padx=Spacing.MD, pady=(2, Spacing.SM))
        self._bind_double_click(countdown_lbl, plant_id=plant["id"])

        status_lbl = ctk.CTkLabel(
            card,
            text="WATER",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            text_color=Colors.ACCENT_BLUE,
            anchor="w",
        )
        status_lbl.grid(row=4, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.SM))
        self._bind_double_click(status_lbl, plant_id=plant["id"])

        logo_path = self._resolve_schedule_image_path(plant)
        cimg = self._get_schedule_image(logo_path or "", (120, 120))
        if cimg is not None:
            logo_lbl = ctk.CTkLabel(card, text="", image=cimg)
            logo_lbl.image = cimg
            logo_lbl.grid(row=0, column=1, rowspan=5, sticky="ns", padx=(Spacing.SM, Spacing.SM), pady=Spacing.XS)
            self._bind_double_click(logo_lbl, plant_id=plant["id"])
        else:
            logo_lbl = ctk.CTkLabel(
                card,
                text="No Image",
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
                text_color=Colors.TEXT_MUTED,
                width=120,
            )
            logo_lbl.grid(row=0, column=1, rowspan=5, sticky="ns", padx=(Spacing.SM, Spacing.SM), pady=Spacing.XS)
            self._bind_double_click(logo_lbl, plant_id=plant["id"])

        watered_var = ctk.BooleanVar(value=False)

        # React when watered toggle
        def on_watered_toggle() -> None:
            if watered_var.get():
                self._water_plant(plant["id"], plant.get("name", ""))

        watered_chk = ctk.CTkCheckBox(
            card,
            text="",
            variable=watered_var,
            onvalue=True,
            offvalue=False,
            command=on_watered_toggle,
            checkbox_width=44,
            checkbox_height=44,
            corner_radius=22,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            border_color=Colors.BORDER,
        )
        watered_chk.grid(row=0, column=2, rowspan=5, padx=(Spacing.XS, Spacing.MD), pady=Spacing.SM)

        if not hasattr(self, "_watered_vars"):
            self._watered_vars = {}
        self._watered_vars[plant["id"]] = watered_var

        self._timer_labels.append((plant["id"], countdown_lbl, status_lbl, card))

        self._apply_card_status_style(card, "OVERDUE" if is_overdue else "WATER")

    # Apply card status style now
    def _apply_card_status_style(self, card: ctk.CTkFrame, status: str) -> None:
        s = str(status or "").upper()
        if s == "OVERDUE":
            card.configure(fg_color=Colors.BG_CARD, border_color=Colors.TEXT_DANGER, border_width=2)
        elif s == "SOON":
            card.configure(fg_color=Colors.BG_CARD, border_color=Colors.TEXT_WARNING, border_width=2)
        else:
            card.configure(fg_color=Colors.BG_CARD, border_color=Colors.ACCENT_BLUE, border_width=2)

    # Handle bind double click
    def _bind_double_click(self, widget: ctk.CTkBaseClass, plant_id: int) -> None:
        widget.bind("<Double-Button-1>", lambda _e, pid=plant_id: self._open_plant_details_dialog(pid))

    # Open plant details dialog
    def _open_plant_details_dialog(self, plant_id: int) -> None:
        plant = db.get_plant(plant_id)
        if not plant:
            return
        try:
            from garden import _PlantDetailDialog
            dlg = _PlantDetailDialog(self, plant)
            self.wait_window(dlg)
            self.refresh()
        except Exception:
            pass

    # Handle water plant
    def _water_plant(self, plant_id: int, plant_name: str = "") -> None:
        try:
            db.mark_watered(plant_id)
            self.refresh()
        except Exception:
            pass

    # Open details sheet
    def _open_details_sheet(self, plant_id: int) -> None:
        """Open a floating details view (in-window) and dim background."""
        if hasattr(self, "_detail_overlay") and self._detail_overlay.winfo_exists():
            try:
                self._detail_overlay.destroy()
            except Exception:
                pass

        self.update_idletasks()

        overlay = ctk.CTkFrame(self, fg_color="#000000")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.configure(fg_color="#000000")
        try:
            overlay.configure(bg_color="#000000")  # best-effort
        except Exception:
            pass
        overlay.attributes = {}  # harmless placeholder for lint
        overlay.bind("<Button-1>", lambda e: overlay.destroy())  # tap outside to close
        self._detail_overlay = overlay

        sheet = ctk.CTkFrame(
            overlay,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.LG,
            border_width=1,
            border_color=Colors.BORDER,
        )
        sheet.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72, relheight=0.78)
        sheet.grid_columnconfigure(0, weight=1)
        self._detail_sheet = sheet

        plant = db.get_plant(plant_id)
        if not plant:
            ctk.CTkLabel(sheet, text="Plant not found.", text_color=Colors.TEXT_MUTED).grid(padx=Spacing.LG, pady=Spacing.LG)
            return

        hdr = ctk.CTkFrame(sheet, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        hdr.grid_columnconfigure(0, weight=1)

        title = plant["name"]
        if plant.get("name_nepali"):
            title += f" ({plant['name_nepali']})"

        ctk.CTkLabel(
            hdr, text=title,
            font=(Fonts.FAMILY, 18, "bold"),
            text_color=Colors.PRIMARY_DARK,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr, text="Close", width=80, height=30,
            fg_color=Colors.BG_INPUT, hover_color=Colors.BUTTON_HOVER,
            corner_radius=Radius.SM,
            command=overlay.destroy,
        ).grid(row=0, column=1, sticky="e")

        body = ctk.CTkFrame(sheet, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=Spacing.LG, pady=(0, Spacing.LG))
        sheet.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            body,
            text=f"Status: {plant.get('status')}\nStreak: {plant.get('streak', 0)}\nTotal waterings: {plant.get('total_waterings', 0)}",
            font=(Fonts.FAMILY, Fonts.SIZE_BODY),
            text_color=Colors.TEXT_SECONDARY,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        actions = ctk.CTkFrame(sheet, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=Spacing.LG, pady=(0, Spacing.LG))
        actions.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            actions, text="Water",
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=Radius.SM, height=34,
            command=lambda: (self._water_plant(plant_id, plant["name"]), overlay.destroy()),
        ).grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        ctk.CTkButton(
            actions, text="Check-in",
            fg_color=Colors.EARTH, hover_color=Colors.EARTH_LIGHT,
            corner_radius=Radius.SM, height=34,
            command=lambda: (self._open_checkin_from_dashboard(plant), overlay.destroy()),
        ).grid(row=0, column=1, sticky="ew", padx=(Spacing.XS, Spacing.XS))

        ctk.CTkButton(
            actions, text="Remove",
            fg_color=Colors.TEXT_DANGER, hover_color="#E53935",
            corner_radius=Radius.SM, height=34,
            command=lambda: (self._delete_plant_from_dashboard(plant), overlay.destroy()),
        ).grid(row=0, column=2, sticky="ew", padx=(Spacing.XS, 0))

    # Open checkin from dashboard
    def _open_checkin_from_dashboard(self, plant: dict) -> None:
        from garden import _CheckinDialog
        dlg = _CheckinDialog(self, plant)
        self.wait_window(dlg)
        self.refresh()

    # Delete plant from dashboard
    def _delete_plant_from_dashboard(self, plant: dict) -> None:
        from garden import _ConfirmDeleteDialog
        dlg = _ConfirmDeleteDialog(self, plant)
        self.wait_window(dlg)
        if getattr(dlg, "confirmed", False):
            db.delete_plant(plant["id"])
            self.refresh()


    # Handle start tick
    def _start_tick(self) -> None:
        if self._tick_id:
            self.after_cancel(self._tick_id)
        self._tick()

    # Handle tick
    def _tick(self) -> None:
        now = datetime.now()

        for plant_id, countdown_lbl, status_lbl, card in self._timer_labels:
            plant = db.get_plant(plant_id)
            if not plant:
                continue
            nw = plant.get("next_water_at")
            if not nw:
                countdown_lbl.configure(text="No schedule", text_color=Colors.TEXT_MUTED)
                status_lbl.configure(text="WATER", text_color=Colors.ACCENT_BLUE)
                self._apply_card_status_style(card, "WATER")
                continue
            try:
                due = datetime.fromisoformat(nw)
            except ValueError:
                continue

            delta = due - now
            total_sec = int(delta.total_seconds())

            if total_sec <= 0:
                overdue_mins = abs(total_sec) // 60
                if overdue_mins < 60:
                    countdown_lbl.configure(
                        text=f"OVERDUE by {overdue_mins}m",
                        text_color=Colors.TEXT_DANGER,
                    )
                else:
                    overdue_h = overdue_mins // 60
                    countdown_lbl.configure(
                        text=f"OVERDUE by {overdue_h}h {overdue_mins % 60}m",
                        text_color=Colors.TEXT_DANGER,
                    )
                status_lbl.configure(
                    text="OVERDUE",
                    text_color=Colors.TEXT_DANGER,
                )
                self._apply_card_status_style(card, "OVERDUE")
                if hasattr(self, "_watered_vars") and plant_id in self._watered_vars:
                    self._watered_vars[plant_id].set(False)
            elif total_sec < 3600:
                mins = total_sec // 60
                secs = total_sec % 60
                countdown_lbl.configure(
                    text=f"Due in {mins}m {secs}s",
                    text_color=Colors.TEXT_WARNING,
                )
                status_lbl.configure(
                    text="SOON",
                    text_color=Colors.ACCENT_YELLOW,
                )
                self._apply_card_status_style(card, "SOON")
                if hasattr(self, "_watered_vars") and plant_id in self._watered_vars:
                    self._watered_vars[plant_id].set(False)
            else:
                hours = total_sec // 3600
                mins = (total_sec % 3600) // 60
                countdown_lbl.configure(
                    text=f"Due in {hours}h {mins}m",
                    text_color=Colors.TEXT_MUTED,
                )
                status_lbl.configure(
                    text="WATER",
                    text_color=Colors.ACCENT_BLUE,
                )
                self._apply_card_status_style(card, "WATER")
                if hasattr(self, "_watered_vars") and plant_id in self._watered_vars:
                    self._watered_vars[plant_id].set(True)

        self._tick_id = self.after(1000, self._tick)


    # Refresh notifications
    def _refresh_notifications(self) -> None:
        """Manual refresh for the Notification Panel (debounced)."""
        if getattr(self, "_loading_messages", False):
            return

        try:
            if getattr(self, "_pending_msg_refresh_id", None):
                self.after_cancel(self._pending_msg_refresh_id)
        except Exception:
            pass

        try:
            self._pending_msg_refresh_id = self.after(50, self._load_messages)
        except Exception:
            self._load_messages()

    # Load messages into this view
    def _load_messages(self) -> None:
        if getattr(self, "_loading_messages", False):
            return

        self._loading_messages = True
        try:
            try:
                for w in self._messages_frame.winfo_children():
                    w.destroy()
                ctk.CTkLabel(
                    self._messages_frame,
                    text="Loading...",
                    font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                    text_color=Colors.TEXT_MUTED,
                ).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=Spacing.SM)
                self._messages_frame.update_idletasks()
            except Exception:
                pass

            try:
                db.auto_update_statuses()
            except Exception:
                pass

            messages = db.get_messages(limit=40, include_family=True)
            try:
                self._last_seen_msg_id = int(messages[0]["id"]) if messages else 0
            except Exception:
                pass

            for w in self._messages_frame.winfo_children():
                w.destroy()

            if not messages:
                ctk.CTkLabel(
                    self._messages_frame,
                    text="No notifications yet.",
                    font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                    text_color=Colors.TEXT_MUTED,
                ).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=Spacing.SM)
                return

            messages = list(reversed(messages))

            for i, msg in enumerate(messages):
                self._create_message_bubble(i, msg)

            self._scroll_messages_to_bottom()

        finally:
            self._loading_messages = False
            self._pending_msg_refresh_id = None

    # Ensure message poll
    def _ensure_message_poll(self) -> None:
        if self._msg_poll_id is None:
            self._msg_poll_id = self.after(1200, self._poll_messages)

    # Handle poll messages
    def _poll_messages(self) -> None:
        self._msg_poll_id = None
        try:
            latest = db.get_messages(limit=1, include_family=True)
            latest_id = int(latest[0]["id"]) if latest else 0
            if self._last_seen_msg_id is None or latest_id != self._last_seen_msg_id:
                self._load_messages()
        except Exception:
            pass
        finally:
            self._msg_poll_id = self.after(1200, self._poll_messages)

    # Create message bubble
    def _create_message_bubble(self, row: int, msg: dict) -> None:
        msg_type = msg.get("msg_type", "info")

        sender_raw = str(msg.get("sender") or "System").strip()
        sender_key = sender_raw.lower()
        sender_colors = {
            "dad": Colors.ACCENT_BLUE,       # blue
            "kid": Colors.ACCENT_ORANGE,     # orange
            "mom": Colors.PRIMARY,           # green
            "john": "#000000",               # black
        }

        type_colors = {
            "success": Colors.TEXT_SUCCESS,
            "warning": Colors.TEXT_WARNING,
            "error": Colors.TEXT_DANGER,
            "info": Colors.ACCENT_BLUE,
        }
        accent = sender_colors.get(sender_key, type_colors.get(msg_type, Colors.ACCENT_BLUE))

        bubble = ctk.CTkFrame(
            self._messages_frame, fg_color=Colors.BG_INPUT,
            corner_radius=Radius.SM,
            border_width=1, border_color=accent,
        )
        bubble.grid(row=row, column=0, sticky="ew", pady=2, padx=Spacing.XS)
        bubble.grid_columnconfigure(1, weight=1)

        dot = ctk.CTkLabel(bubble, text="\u25CF", text_color=accent,
                           font=(Fonts.FAMILY, 10), width=12)
        dot.grid(row=0, column=0, rowspan=3, padx=(Spacing.SM, 2), pady=Spacing.XS)

        time_str = ""
        try:
            if msg.get("created_at"):
                dt = datetime.fromisoformat(str(msg.get("created_at")))
                time_str = dt.strftime("%H:%M")
        except Exception:
            time_str = ""

        header_text = sender_raw or "System"
        if time_str:
            header_text = f"{header_text}  ·  {time_str}"

        sender = ctk.CTkLabel(
            bubble, text=header_text,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            text_color=accent, anchor="w",
        )
        sender.grid(row=0, column=1, sticky="w", padx=Spacing.XS, pady=(Spacing.XS, 0))

        scope = "Garden"
        try:
            if msg.get("user_id"):
                scope = "Personal"
        except Exception:
            pass

        scope_lbl = ctk.CTkLabel(
            bubble, text=scope,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        scope_lbl.grid(row=1, column=1, sticky="w", padx=Spacing.XS)

        content = ctk.CTkLabel(
            bubble, text=str(msg.get("content") or ""),
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_LIGHT, anchor="w", wraplength=280,
        )
        content.grid(row=2, column=1, sticky="w", padx=Spacing.XS, pady=(0, Spacing.XS))

    # Handle send message
    def _send_message(self) -> None:
        text = ""
        try:
            text = self._msg_entry.get().strip()
        except Exception:
            text = ""
        if not text:
            return

        user = None
        try:
            user = db.get_current_user()
        except Exception:
            user = None
        sender = "You"
        if isinstance(user, dict) and user.get("username"):
            sender = str(user.get("username"))

        gid = None
        uid = None
        try:
            gid = db.get_current_garden_id() if hasattr(db, "get_current_garden_id") else None
        except Exception:
            gid = None
        try:
            uid = db.get_current_user_id() if hasattr(db, "get_current_user_id") else None
        except Exception:
            uid = None

        try:
            db.add_message(text, sender=sender, msg_type="info", user_id=uid, garden_id=gid)
        except TypeError:
            try:
                db.add_message(text, sender, "info")
            except Exception:
                return

        try:
            self._msg_entry.delete(0, "end")
        except Exception:
            pass
        self._load_messages()

    # Handle destroy
    def destroy(self):
        if self._tick_id:
            self.after_cancel(self._tick_id)
        if self._pending_msg_refresh_id:
            try:
                self.after_cancel(self._pending_msg_refresh_id)
            except Exception:
                pass
        if self._msg_poll_id:
            try:
                self.after_cancel(self._msg_poll_id)
            except Exception:
                pass
        super().destroy()

    # Toggle add menu
    def _toggle_add_menu(self) -> None:
        """Show/hide the Add Plant submenu (From Catalogue / Custom Plant)."""
        self._add_menu_open = not getattr(self, "_add_menu_open", False)

        if self._add_menu_open:
            self._add_from_cat_btn.grid(row=1, column=0, sticky="e", pady=(Spacing.XS, 0))
            self._add_custom_btn.grid(row=2, column=0, sticky="e", pady=(Spacing.XS, 0))
        else:
            self._add_from_cat_btn.grid_remove()
            self._add_custom_btn.grid_remove()

    # Open catalogue add
    def _open_catalogue_add(self) -> None:
        """Open the existing Catalogue page (CatalogueFrame) as a floating in-window sheet."""
        if getattr(self, "_add_menu_open", False):
            self._toggle_add_menu()

        self._open_catalogue_sheet()

    # Open catalogue sheet
    def _open_catalogue_sheet(self) -> None:
        if hasattr(self, "_sheet_overlay") and self._sheet_overlay and self._sheet_overlay.winfo_exists():
            try:
                self._sheet_overlay.destroy()
            except Exception:
                pass

        self.update_idletasks()

        overlay = ctk.CTkFrame(self, fg_color="#101010")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.bind("<Button-1>", lambda _e: self._close_sheet())
        self._sheet_overlay = overlay

        sheet = ctk.CTkFrame(
            overlay,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.LG,
            border_width=1,
            border_color=Colors.BORDER,
        )
        sheet.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.88, relheight=0.90)
        sheet.grid_columnconfigure(0, weight=1)
        sheet.grid_rowconfigure(1, weight=1)
        self._sheet = sheet

        sheet.bind("<Button-1>", lambda _e: "break")

        header = ctk.CTkFrame(sheet, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        header.grid_columnconfigure(0, weight=1)
        header.bind("<Button-1>", lambda _e: "break")

        ctk.CTkLabel(
            header,
            text="Catalogue",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.PRIMARY_DARK,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="Close",
            width=90,
            height=32,
            fg_color=Colors.BG_INPUT,
            hover_color=Colors.BUTTON_HOVER,
            corner_radius=Radius.SM,
            command=self._close_sheet,
        ).grid(row=0, column=1, sticky="e")

        body = ctk.CTkFrame(sheet, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=Spacing.LG, pady=(0, Spacing.LG))
        body.bind("<Button-1>", lambda _e: "break")

        from catalogue import CatalogueFrame
        self._catalogue_sheet_frame = CatalogueFrame(
            body,
            on_navigate=self._on_navigate,  # keep same navigation if catalogue uses it
            on_item_selected=self._add_catalogue_item_to_garden,
        )
        self._catalogue_sheet_frame.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        if hasattr(self._catalogue_sheet_frame, "refresh"):
            try:
                self._catalogue_sheet_frame.refresh()
            except Exception:
                pass
            
    # Open custom add
    def _open_custom_add(self) -> None:
        """Open Custom Plant as a floating in-window sheet (dim background)."""
        if getattr(self, "_add_menu_open", False):
            self._toggle_add_menu()

        self._open_custom_sheet()

    # Open custom sheet
    def _open_custom_sheet(self) -> None:
        """
        Open Custom Plant as an in-window floating sheet (dim background).
        Custom form requirements:
          - Watering frequency via slider
          - Dropdown for Season
          - Dropdown for Water needed
          - Text area for Notes
        """
        for attr in ("_sheet_overlay", "_detail_overlay"):
            if hasattr(self, attr):
                try:
                    ov = getattr(self, attr)
                    if ov and ov.winfo_exists():
                        ov.destroy()
                except Exception:
                    pass

        self.update_idletasks()

        overlay = ctk.CTkFrame(self, fg_color="#101010")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.bind("<Button-1>", lambda _e: self._close_sheet())
        self._sheet_overlay = overlay

        sheet = ctk.CTkFrame(
            overlay,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.LG,
            border_width=1,
            border_color=Colors.BORDER,
        )
        sheet.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.66, relheight=0.80)
        sheet.grid_columnconfigure(0, weight=1)
        sheet.grid_rowconfigure(1, weight=1)
        self._sheet = sheet

        sheet.bind("<Button-1>", lambda _e: "break")

        header = ctk.CTkFrame(sheet, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        header.grid_columnconfigure(0, weight=1)
        header.bind("<Button-1>", lambda _e: "break")

        ctk.CTkLabel(
            header,
            text="Add Custom Plant",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.PRIMARY_DARK,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="Close",
            width=90,
            height=32,
            fg_color=Colors.BG_INPUT,
            hover_color=Colors.BUTTON_HOVER,
            corner_radius=Radius.SM,
            command=self._close_sheet,
        ).grid(row=0, column=1, sticky="e")

        body = ctk.CTkFrame(sheet, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=Spacing.LG, pady=(0, Spacing.LG))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(99, weight=1)  # spacer
        body.bind("<Button-1>", lambda _e: "break")

        name_e = ctk.CTkEntry(
            body, placeholder_text="Plant name (required)",
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=Radius.SM, height=36,
        )
        name_e.grid(row=0, column=0, sticky="ew", pady=(0, Spacing.SM))

        nep_e = ctk.CTkEntry(
            body, placeholder_text="Nepali name (optional)",
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=Radius.SM, height=36,
        )
        nep_e.grid(row=1, column=0, sticky="ew", pady=(0, Spacing.SM))

        sci_e = ctk.CTkEntry(
            body, placeholder_text="Scientific name (optional)",
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=Radius.SM, height=36,
        )
        sci_e.grid(row=2, column=0, sticky="ew", pady=(0, Spacing.SM))

        wf_wrap = ctk.CTkFrame(body, fg_color="transparent")
        wf_wrap.grid(row=3, column=0, sticky="ew", pady=(0, Spacing.SM))
        wf_wrap.grid_columnconfigure(0, weight=1)
        wf_wrap.bind("<Button-1>", lambda _e: "break")

        wf_label = ctk.CTkLabel(
            wf_wrap,
            text="Watering frequency: 3 days",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        )
        wf_label.grid(row=0, column=0, sticky="w", pady=(0, 6))

        wf_val = ctk.IntVar(value=3)

        # Handle wf changed
        def _wf_changed(v: float) -> None:
            days = int(round(float(v)))
            wf_val.set(days)
            wf_label.configure(text=f"Watering frequency: {days} day" + ("" if days == 1 else "s"))

        wf_slider = ctk.CTkSlider(
            wf_wrap,
            from_=1,
            to=14,
            number_of_steps=13,
            command=_wf_changed,
            progress_color=Colors.PRIMARY,
            fg_color=Colors.BG_INPUT,
        )
        wf_slider.set(3)
        wf_slider.grid(row=1, column=0, sticky="ew")

        season_dd = ctk.CTkOptionMenu(
            body,
            values=["All", "Spring", "Summer", "Monsoon", "Autumn", "Winter"],
            fg_color=Colors.BG_INPUT,
            button_color=Colors.BG_INPUT,
            button_hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            dropdown_fg_color=Colors.BG_CARD,
            dropdown_text_color=Colors.TEXT_PRIMARY,
            corner_radius=Radius.SM,
            height=36,
        )
        season_dd.set("All")
        season_dd.grid(row=4, column=0, sticky="ew", pady=(0, Spacing.SM))

        water_need_dd = ctk.CTkOptionMenu(
            body,
            values=["Low", "Medium", "High"],
            fg_color=Colors.BG_INPUT,
            button_color=Colors.BG_INPUT,
            button_hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            dropdown_fg_color=Colors.BG_CARD,
            dropdown_text_color=Colors.TEXT_PRIMARY,
            corner_radius=Radius.SM,
            height=36,
        )
        water_need_dd.set("Medium")
        water_need_dd.grid(row=5, column=0, sticky="ew", pady=(0, Spacing.SM))

        ctk.CTkLabel(
            body,
            text="Notes",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(row=6, column=0, sticky="w", pady=(0, 6))

        notes_t = ctk.CTkTextbox(
            body,
            height=80,  # was 120
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            border_width=1,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
        )
        notes_t.grid(row=7, column=0, sticky="ew", pady=(0, Spacing.SM))  # was nsew

        err = ctk.CTkLabel(body, text="", text_color=Colors.TEXT_DANGER, anchor="w")
        err.grid(row=8, column=0, sticky="ew", pady=(0, Spacing.SM))

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=9, column=0, sticky="ew")
        actions.grid_columnconfigure((0, 1), weight=1)

        # Save the current data
        def save() -> None:
            name = name_e.get().strip()
            if not name:
                err.configure(text="Name is required.")
                return

            water_need = (water_need_dd.get() or "medium").strip().lower()
            water_need = water_need if water_need in {"low", "medium", "high"} else "medium"

            db.add_plant(
                name=name,
                name_nepali=nep_e.get().strip() or "",
                scientific_name=sci_e.get().strip() or "",
                water_freq_hours=max(1, int(wf_val.get())) * 24,
                notes=notes_t.get("1.0", "end").strip(),
                season=season_dd.get(),
                water_need=water_need,
            )
            self._close_sheet()  # refresh happens in _close_sheet()

        ctk.CTkButton(
            actions,
            text="Cancel",
            height=34,
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color=Colors.TEXT_DARK, # readable on light bg
            corner_radius=Radius.SM,
            command=self._close_sheet,
        ).grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        ctk.CTkButton(
            actions,
            text="Create Plant",
            height=34,
            fg_color=Colors.ACCENT_YELLOW,
            hover_color=Colors.ACCENT_YELLOW,
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=save,
        ).grid(row=0, column=1, sticky="ew", padx=(Spacing.XS, 0))

    # Close sheet
    def _close_sheet(self) -> None:
        """Close floating sheet and refresh dashboard (so newly added plants show)."""
        try:
            if hasattr(self, "_sheet_overlay") and self._sheet_overlay and self._sheet_overlay.winfo_exists():
                self._sheet_overlay.destroy()
        finally:
            self._sheet_overlay = None
            self._sheet = None
            self._catalogue_sheet_frame = None
            self.refresh()

    # Build catalogue panel for this screen
    def _build_catalogue_panel(self, parent: ctk.CTkFrame) -> None:
        """
        Minimal in-panel catalogue picker (no Toplevel).
        Uses db.search_catalogue() and db.add_plant(...) like existing flows.
        """
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        search = ctk.CTkEntry(
            parent,
            placeholder_text="Search catalogue...",
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
            height=36,
        )
        search.grid(row=0, column=0, sticky="ew", pady=(0, Spacing.SM))

        results = ctk.CTkScrollableFrame(parent, fg_color=Colors.BG_INPUT, corner_radius=Radius.MD)
        results.grid(row=1, column=0, sticky="nsew")
        results.grid_columnconfigure(0, weight=1)

        # Render the current data
        def render(items: list[dict]) -> None:
            for w in results.winfo_children():
                w.destroy()

            if not items:
                ctk.CTkLabel(
                    results,
                    text="No results.",
                    text_color=Colors.TEXT_MUTED,
                    font=(Fonts.FAMILY, Fonts.SIZE_BODY),
                ).grid(row=0, column=0, pady=Spacing.LG)
                return

            for i, item in enumerate(items):
                rowf = ctk.CTkFrame(results, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
                rowf.grid(row=i, column=0, sticky="ew", pady=Spacing.XS, padx=Spacing.XS)
                rowf.grid_columnconfigure(0, weight=1)

                title = item.get("name", "")
                if item.get("name_nepali"):
                    title += f" ({item['name_nepali']})"

                subtitle = item.get("scientific_name") or ""

                ctk.CTkLabel(
                    rowf,
                    text=title,
                    font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
                    text_color=Colors.TEXT_LIGHT,
                    anchor="w",
                ).grid(row=0, column=0, sticky="w", padx=Spacing.SM, pady=(Spacing.SM, 0))

                if subtitle:
                    ctk.CTkLabel(
                        rowf,
                        text=subtitle,
                        font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "italic"),
                        text_color=Colors.TEXT_MUTED,
                        anchor="w",
                    ).grid(row=1, column=0, sticky="w", padx=Spacing.SM, pady=(2, Spacing.SM))

                add_btn = ctk.CTkButton(
                    rowf,
                    text="Add",
                    width=80,
                    height=32,
                    fg_color=Colors.PRIMARY,
                    hover_color=Colors.PRIMARY_HOVER,
                    corner_radius=Radius.SM,
                    command=lambda it=item: self._add_catalogue_item_to_garden(it),
                )
                add_btn.grid(row=0, column=1, rowspan=2, padx=Spacing.SM, pady=Spacing.SM)

        # Handle do search
        def do_search(_e=None) -> None:
            q = search.get().strip()
            items = db.search_catalogue(q) if q else db.search_catalogue()
            render(list(items))

        search.bind("<Return>", do_search)

        render(list(db.search_catalogue()))

    # Add catalogue item to garden
    def _add_catalogue_item_to_garden(self, item: dict) -> None:
        """
        Add selected catalogue plant to garden, then close the floating panel.
        """
        try:
            item_id = int(item.get("id") or item.get("catalogue_id") or 0)
        except Exception:
            item_id = 0

        added_id = None
        if item_id > 0:
            added_id = db.add_plant_from_catalogue(item_id, "")

        if not added_id:
            added_id = db.add_plant(
                name=item.get("name", ""),
                name_nepali=item.get("name_nepali", ""),
                scientific_name=item.get("scientific_name", ""),
                water_freq_hours=float(item.get("water_freq_hours", 24) or 24),
                notes="",
                season=item.get("season", ""),
                soil_type=item.get("soil_type", ""),
                water_need=item.get("water_need", "medium"),
                image_path=item.get("image_path", ""),
            )

        if added_id:
            db.add_message(
                f"'{item.get('name', 'Plant')}' added to My Garden.",
                "Catalogue",
                "success",
            )
            self._close_sheet()

    # Handle is overdue
    def _is_overdue(self, plant: dict) -> bool:
        """
        Best-effort overdue check used by schedule cards.
        Supports either:
          - a direct due date field (next_water_due / water_due / due_at), or
          - last_watered_at + watering_interval_days
        """
        due = plant.get("next_water_due") or plant.get("water_due") or plant.get("due_at")
        if due:
            try:
                due_dt = datetime.fromisoformat(str(due).replace("Z", "+00:00"))
                now = datetime.now(due_dt.tzinfo) if due_dt.tzinfo else datetime.now()
                return now > due_dt
            except Exception:
                pass

        last = plant.get("last_watered_at") or plant.get("last_watered")
        interval = plant.get("watering_interval_days") or plant.get("interval_days")

        try:
            interval_days = int(interval or 0)
        except Exception:
            interval_days = 0

        if not last or interval_days <= 0:
            return False

        try:
            last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
        except Exception:
            return False

        due_dt = last_dt + timedelta(days=interval_days)
        now = datetime.now(due_dt.tzinfo) if due_dt.tzinfo else datetime.now()
        return now > due_dt

    # Handel scroll messages to bottom
    def _scroll_messages_to_bottom(self) -> None:
        """Scroll the Notification Panel to the bottom (newest message)."""
        try:
            canvas = getattr(self._messages_frame, "_parent_canvas", None)
            if canvas is not None:
                canvas.update_idletasks()
                canvas.yview_moveto(1.0)
                return
        except Exception:
            pass

        try:
            self._messages_frame.update_idletasks()
        except Exception:
            pass
