"""
dev_panel.py  Developer / Debug Panel for Karesabari.

Features:
  - Database overview: row counts for every table
  - Raw table viewer: select any table and see rows in a scrollable text area
  - Quick actions: Seed demo garden, Nuke all data, Clear messages, Clear events
  - Time Warp: move a plant's next_water_at backward to simulate overdue
  - Force status update: run auto_update_statuses()
  - Event log viewer with live refresh
  - DB file path and size info
  - Window size switcher for testing responsive UI
"""

from __future__ import annotations

import os
import json
import customtkinter as ctk
from datetime import datetime
from typing import Callable, Optional

from theme import Colors, Fonts, Spacing, Radius
import database as db
from window_config import get_preset_names, get_window_size, WINDOW_PRESETS


class DevPanelFrame(ctk.CTkFrame):
    """Developer debug panel."""

    # Set up this object and prepare its initial state
    def __init__(self, master: ctk.CTkFrame, on_navigate: Optional[Callable] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_navigate = on_navigate

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew",
                           padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        ctk.CTkLabel(
            header_frame, text="Dev Panel",
            font=(Fonts.FAMILY, Fonts.SIZE_TITLE, "bold"),
            text_color=Colors.TEXT_DANGER, anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="    Debug & Testing Tools",
            font=(Fonts.FAMILY, Fonts.SIZE_BODY),
            text_color=Colors.TEXT_MUTED, anchor="w",
        ).pack(side="left", padx=Spacing.SM)

        ctk.CTkButton(
            header_frame, text="Refresh All", width=100,
            fg_color="#DCFCE7", hover_color="#BBF7D0",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            command=self.refresh,
        ).pack(side="right")

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, columnspan=2, sticky="ew",
                   padx=Spacing.LG, pady=(0, Spacing.SM))
        left.grid_columnconfigure((0, 1), weight=1)

        db_card = ctk.CTkFrame(left, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
        db_card.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.SM), pady=Spacing.XS)

        ctk.CTkLabel(db_card, text="Database Info",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.ACCENT_BLUE).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

        self._db_info_label = ctk.CTkLabel(
            db_card, text="...",
            font=(Fonts.FAMILY_MONO, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_LIGHT, anchor="w", justify="left",
        )
        self._db_info_label.pack(anchor="w", padx=Spacing.MD, pady=(0, Spacing.SM))

        actions_card = ctk.CTkFrame(left, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
        actions_card.grid(row=0, column=1, sticky="ew", padx=(Spacing.SM, 0), pady=Spacing.XS)

        ctk.CTkLabel(actions_card, text="Quick Actions",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.ACCENT_ORANGE).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

        actions_inner = ctk.CTkFrame(actions_card, fg_color="transparent")
        actions_inner.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.SM))

        buttons = [
            ("Seed Demo Garden", Colors.PRIMARY, self._seed_demo),
            ("Nuke All Data", Colors.TEXT_DANGER, self._nuke),
            ("Clear Messages", Colors.EARTH, self._clear_msgs),
            ("Clear Event Log", Colors.EARTH, self._clear_events),
            ("Force Status Check", Colors.ACCENT_BLUE, self._force_status),
        ]
        for i, (text, color, cmd) in enumerate(buttons):
            ctk.CTkButton(
                actions_inner, text=text, height=28,
                fg_color=color, hover_color=Colors.BORDER,
                corner_radius=Radius.SM,
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
                command=cmd,
            ).pack(fill="x", pady=2)

        warp_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
        warp_frame.grid(row=1, column=0, columnspan=2, sticky="ew",
                         padx=Spacing.LG, pady=(Spacing.SM, Spacing.SM))
        warp_frame.grid(row=1, column=0, columnspan=2)


        left.destroy()
        warp_frame.destroy()

        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.grid(row=1, column=0, columnspan=2, sticky="ew",
                   padx=Spacing.LG, pady=(0, Spacing.SM))
        row1.grid_columnconfigure((0, 1, 2, 3), weight=1)

        db_card = ctk.CTkFrame(row1, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
        db_card.grid(row=0, column=0, sticky="nsew", padx=(0, Spacing.XS))

        ctk.CTkLabel(db_card, text="Database",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.ACCENT_BLUE).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

        self._db_info_label = ctk.CTkLabel(
            db_card, text="...",
            font=(Fonts.FAMILY_MONO, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_LIGHT, anchor="w", justify="left",
        )
        self._db_info_label.pack(anchor="w", padx=Spacing.MD, pady=(0, Spacing.SM))

        actions_card = ctk.CTkFrame(row1, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
        actions_card.grid(row=0, column=1, sticky="nsew", padx=Spacing.XS)

        ctk.CTkLabel(actions_card, text="Quick Actions",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.ACCENT_ORANGE).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

        quick_actions: list[tuple[str, str, str, Callable]] = [
            ("Seed Demo Garden", Colors.PRIMARY, Colors.PRIMARY_HOVER, self._seed_demo),
            ("Nuke All Data", Colors.TEXT_DANGER, "#E53935", self._nuke),
            ("Clear Messages", Colors.ACCENT_YELLOW, Colors.ACCENT_ORANGE, self._clear_msgs),
            ("Clear Event Log", Colors.ACCENT_BLUE, "#5AB0F5", self._clear_events),
            ("Force Status Check", Colors.BG_INPUT, Colors.BUTTON_HOVER, self._force_status),
        ]
        for text, base_color, hover_color, cmd in quick_actions:
            ctk.CTkButton(
                actions_card, text=text, height=26,
                fg_color=base_color, hover_color=hover_color,
                corner_radius=Radius.SM,
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
                command=cmd,
            ).pack(fill="x", padx=Spacing.MD, pady=1)

        ctk.CTkFrame(actions_card, fg_color="transparent", height=Spacing.SM).pack()

        warp_card = ctk.CTkFrame(row1, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
        warp_card.grid(row=0, column=2, sticky="nsew", padx=(Spacing.XS, 0))

        ctk.CTkLabel(warp_card, text="Time Warp",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.TEXT_WARNING).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

        ctk.CTkLabel(warp_card, text="Plant ID:",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=Spacing.MD)
        self._warp_plant = ctk.CTkEntry(warp_card, fg_color=Colors.BG_INPUT,
                                         border_color=Colors.BORDER, corner_radius=Radius.SM,
                                         width=80, placeholder_text="ID")
        self._warp_plant.pack(anchor="w", padx=Spacing.MD, pady=2)

        ctk.CTkLabel(warp_card, text="Hours back:",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=Spacing.MD)
        self._warp_hours = ctk.CTkEntry(warp_card, fg_color=Colors.BG_INPUT,
                                         border_color=Colors.BORDER, corner_radius=Radius.SM,
                                         width=80, placeholder_text="e.g. 25")
        self._warp_hours.pack(anchor="w", padx=Spacing.MD, pady=2)

        ctk.CTkButton(
            warp_card, text="Warp!", height=26,
            fg_color=Colors.TEXT_WARNING, hover_color=Colors.ACCENT_ORANGE,
            corner_radius=Radius.SM, text_color=Colors.BG_DARK,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=self._do_time_warp,
        ).pack(padx=Spacing.MD, pady=(Spacing.XS, Spacing.SM))

        size_card = ctk.CTkFrame(row1, fg_color=Colors.BG_CARD, corner_radius=Radius.MD)
        size_card.grid(row=0, column=3, sticky="nsew", padx=(Spacing.XS, 0))

        ctk.CTkLabel(size_card, text="Window Size",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.ACCENT_YELLOW).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

        ctk.CTkLabel(size_card, text="Test different\nscreen sizes:",
                     font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=Spacing.MD, pady=2)

        self._size_select = ctk.CTkOptionMenu(
            size_card,
            values=get_preset_names(),
            fg_color=Colors.BG_INPUT, button_color=Colors.ACCENT_YELLOW,
            button_hover_color=Colors.ACCENT_ORANGE, corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color="black",
            command=self._on_size_selected,
        )
        self._size_select.set("Desktop_1080p")
        self._size_select.pack(fill="x", padx=Spacing.MD, pady=2)

        self._size_info_label = ctk.CTkLabel(
            size_card, text="1150 x 750",
            font=(Fonts.FAMILY_MONO, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_LIGHT,
        )
        self._size_info_label.pack(anchor="w", padx=Spacing.MD, pady=2)

        ctk.CTkButton(
            size_card, text="Apply Size", height=26,
            fg_color=Colors.ACCENT_YELLOW, hover_color=Colors.ACCENT_ORANGE,
            corner_radius=Radius.SM, text_color=Colors.BG_DARK,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=self._apply_window_size,
        ).pack(padx=Spacing.MD, pady=(Spacing.XS, Spacing.SM))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, columnspan=2, sticky="nsew",
                     padx=Spacing.LG, pady=(0, Spacing.LG))
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=2)
        bottom.grid_rowconfigure(1, weight=1)

        tv_header = ctk.CTkFrame(bottom, fg_color="transparent")
        tv_header.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.SM))

        ctk.CTkLabel(tv_header, text="Table Viewer",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.PRIMARY_DARK).pack(side="left")

        self._table_select = ctk.CTkOptionMenu(
            tv_header,
            values=["plants", "watering_log", "weekly_checkins", "messages", "catalogue", "event_log"],
            fg_color=Colors.BG_INPUT, button_color=Colors.PRIMARY,
            button_hover_color=Colors.PRIMARY_HOVER, corner_radius=Radius.SM,
            text_color="black",
            command=self._on_table_change,
        )
        self._table_select.pack(side="left", padx=Spacing.SM)

        ctk.CTkButton(
            tv_header, text="Load", width=60,
            fg_color=Colors.ACCENT_BLUE, hover_color="#5AB0F5",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            command=self._load_table,
        ).pack(side="left")

        self._table_text = ctk.CTkTextbox(
            bottom, fg_color=Colors.BG_CARD, corner_radius=Radius.SM,
            font=(Fonts.FAMILY_MONO, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_LIGHT,
            wrap="none",
        )
        self._table_text.grid(row=1, column=0, sticky="nsew", padx=(0, Spacing.SM), pady=Spacing.XS)

        ctk.CTkLabel(bottom, text="Event Log",
                     font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
                     text_color=Colors.ACCENT_YELLOW).grid(
            row=0, column=1, sticky="w")

        self._event_text = ctk.CTkTextbox(
            bottom, fg_color=Colors.BG_CARD, corner_radius=Radius.SM,
            font=(Fonts.FAMILY_MONO, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_LIGHT,
            wrap="word",
        )
        self._event_text.grid(row=1, column=1, sticky="nsew", pady=Spacing.XS)

        self.refresh()


    # Refresh the current data
    def refresh(self) -> None:
        self._load_db_info()
        self._load_table()
        self._load_events()

    # Load db info into this view
    def _load_db_info(self) -> None:
        counts = db.get_table_counts()
        db_size = "N/A"
        if os.path.exists(db.DB_PATH):
            size_bytes = os.path.getsize(db.DB_PATH)
            if size_bytes < 1024:
                db_size = f"{size_bytes} B"
            else:
                db_size = f"{size_bytes / 1024:.1f} KB"

        lines = [f"Path: .../{os.path.basename(db.DB_PATH)}", f"Size: {db_size}", ""]
        for table, count in counts.items():
            lines.append(f"{table}: {count} rows")

        self._db_info_label.configure(text="\n".join(lines))

    # Load table into this view
    def _load_table(self) -> None:
        table = self._table_select.get()
        rows = db.get_raw_table(table, limit=50)
        self._table_text.delete("1.0", "end")
        if not rows:
            self._table_text.insert("1.0", f"Table '{table}' is empty.")
            return

        if rows:
            keys = list(rows[0].keys())
            header = " | ".join(f"{k:>15}" for k in keys)
            self._table_text.insert("end", header + "\n")
            self._table_text.insert("end", "-" * len(header) + "\n")
            for row in rows:
                vals = []
                for k in keys:
                    v = str(row.get(k, ""))
                    if len(v) > 15:
                        v = v[:12] + "..."
                    vals.append(f"{v:>15}")
                self._table_text.insert("end", " | ".join(vals) + "\n")

    # React when table change
    def _on_table_change(self, val: str) -> None:
        self._load_table()

    # Load events into this view
    def _load_events(self) -> None:
        events = db.get_events(limit=80)
        self._event_text.delete("1.0", "end")
        if not events:
            self._event_text.insert("1.0", "No events recorded yet.")
            return
        for ev in events:
            try:
                dt = datetime.fromisoformat(ev["timestamp"])
                ts = dt.strftime("%H:%M:%S")
            except ValueError:
                ts = ev["timestamp"]
            line = f"[{ts}] {ev['event_type']}: {ev.get('details', '')}\n"
            self._event_text.insert("end", line)


    # Seed demo
    def _seed_demo(self) -> None:
        try:
            created = int(db.seed_demo_garden())
        except Exception as e:
            self._log_and_refresh(f"Seed demo failed: {e}")
            return
        self._log_and_refresh(f"Seeded demo garden ({created} plant(s) added)")

    # Handle nuke
    def _nuke(self) -> None:
        dialog = _ConfirmNukeDialog(self)
        self.wait_window(dialog)
        if dialog.confirmed:
            db.nuke_all_data(family_only=dialog.family_only.get(), delete_messages=dialog.delete_messages.get(), delete_events=dialog.delete_events.get())
            self._log_and_refresh("Nuke executed with selected options")

    # Clear msgs
    def _clear_msgs(self) -> None:
        try:
            deleted = int(db.clear_messages())
        except Exception as e:
            self._log_and_refresh(f"Clear messages failed: {e}")
            return
        self._log_and_refresh(f"Cleared messages ({deleted} row(s))")

    # Clear events
    def _clear_events(self) -> None:
        try:
            db.clear_events()
        except Exception as e:
            self._log_and_refresh(f"Clear events failed: {e}")
            return
        self._log_and_refresh("Cleared event log")

    # Handle force status
    def _force_status(self) -> None:
        try:
            changed = db.auto_update_statuses()
        except Exception as e:
            self._log_and_refresh(f"Force status check failed: {e}")
            return
        self._log_and_refresh(f"Forced status check: {changed} plant(s) updated")

    # Handle do time warp
    def _do_time_warp(self) -> None:
        try:
            pid = int(self._warp_plant.get())
            hours = float(self._warp_hours.get())
        except (ValueError, TypeError):
            self._log_and_refresh("Time warp failed: enter valid Plant ID and Hours")
            return
        try:
            ok = bool(db.time_warp_plant(pid, hours))
        except Exception as e:
            self._log_and_refresh(f"Time warp failed: {e}")
            return
        if ok:
            self._log_and_refresh(f"Time-warped plant #{pid} by {hours}h")
        else:
            self._log_and_refresh(f"Time warp skipped: plant #{pid} not found in current garden")

    # Log and refresh
    def _log_and_refresh(self, msg: str) -> None:
        db.add_message(f"[DEV] {msg}", "Dev Panel", "warning")
        self.refresh()
        if self._on_navigate:
            self._on_navigate("refresh_all")


    # React when size selected
    def _on_size_selected(self, preset_name: str) -> None:
        """Update the info label when a size is selected."""
        width, height = get_window_size(preset_name)
        self._size_info_label.configure(text=f"{width} x {height}")

    # Apply window size
    def _apply_window_size(self) -> None:
        """Apply the selected window size to the current window."""
        preset_name = self._size_select.get()
        width, height = get_window_size(preset_name)
        
        root = self.winfo_toplevel()
        root.geometry(f"{width}x{height}")
        root.minsize(width, height)
        
        db.add_message(f"[DEV] Window resized to {preset_name} ({width}x{height})", "Dev Panel", "info")
        self._log_and_refresh(f"Window resized to {preset_name} ({width}x{height})")



class _ConfirmNukeDialog(ctk.CTkToplevel):
    # Set up this object and prepare its initial state
    def __init__(self, parent):
        super().__init__(parent)
        self.confirmed = False
        self.title("CONFIRM: Nuke All Data")
        self.geometry("460x220")
        self.resizable(True, True)
        self.configure(fg_color=Colors.BG_DARK)
        self.grab_set()

        ctk.CTkLabel(
            self, text="Delete garden data?",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.TEXT_DANGER,
        ).pack(pady=(Spacing.XL, Spacing.SM))

        ctk.CTkLabel(
            self, text="Select which data to remove. Catalogue and users are preserved.",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
        ).pack(pady=Spacing.XS)

        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(pady=(Spacing.SM, 0))

        self.family_only = ctk.BooleanVar(value=True)
        self.delete_messages = ctk.BooleanVar(value=False)
        self.delete_events = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(opts, text="Only current family", variable=self.family_only).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=2)
        ctk.CTkCheckBox(opts, text="Also delete messages", variable=self.delete_messages).grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=2)
        ctk.CTkCheckBox(opts, text="Also delete event log", variable=self.delete_events).grid(row=2, column=0, sticky="w", padx=Spacing.MD, pady=2)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=Spacing.MD)

        ctk.CTkButton(
            btn_frame, text="Cancel", width=120,
            fg_color="#DCEBFF", hover_color="#C9DFFF",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=self.destroy,
        ).pack(side="left", padx=Spacing.SM)

        ctk.CTkButton(
            btn_frame, text="CONFIRM DELETE", width=160,
            fg_color=Colors.TEXT_DANGER, hover_color="#C62828",
            corner_radius=Radius.SM,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            command=self._confirm,
        ).pack(side="left")

    # Handle confirm
    def _confirm(self) -> None:
        self.confirmed = True
        self.destroy()
