"""
sidebar.py  Modern sidebar navigation for Karesabari.

Navigation:
    Dashboard, AI Lab, Catalogue, Settings, Dev Panel
Includes:
  - Overdue plant notification badge on Dashboard
  - Theme toggle
"""
from __future__ import annotations

import customtkinter as ctk
from typing import Callable

from theme import Colors, Fonts, Spacing, Radius
import database as db


class Sidebar(ctk.CTkFrame):
    """Left-side navigation sidebar with notification badges."""

    NAV_ITEMS = [
        ("dashboard",  "Dashboard",   "\u2302"),
        ("ai_lab",     "AI Lab",      "\u2697"),
        ("catalogue",  "Catalogue",   "\u2637"),
        ("settings",   "Settings",    "\u2699"),
        ("dev_panel",  "Dev Panel",   "\u2699"),
    ]

    # Set up this object and prepare its initial state
    def __init__(self, master: ctk.CTkFrame, on_select: Callable[[str], None], on_logout: Callable = None, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,          
            corner_radius=Radius.LG,       
            border_width=1,                         
            border_color=Colors.BORDER,
            width=300,
            **kwargs
        )

        self.grid_propagate(False)
        self._on_select = on_select
        self._on_logout = on_logout
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._badges: dict[str, ctk.CTkLabel] = {}
        self._active: str = "dashboard"

        self.grid_columnconfigure(0, weight=1)

        brand_frame = ctk.CTkFrame(self, fg_color="transparent")
        brand_frame.grid(row=0, column=0, sticky="ew", padx=Spacing.MD,
                         pady=(Spacing.XL, Spacing.XS))

        ctk.CTkLabel(
            brand_frame, text="\u2630  Menu",
            font=(Fonts.FAMILY, 18, "bold"),
            text_color=Colors.TEXT_LIGHT,
        ).pack(side="left")

        sep = ctk.CTkFrame(self, fg_color=Colors.BORDER, height=1)
        sep.grid(row=1, column=0, sticky="ew", padx=Spacing.MD, pady=(0, Spacing.MD))

        for idx, (key, label, icon) in enumerate(self.NAV_ITEMS):
            nav_frame = ctk.CTkFrame(self, fg_color="transparent")
            nav_frame.grid(row=2 + idx, column=0, sticky="ew", padx=Spacing.SM, pady=1)
            nav_frame.grid_columnconfigure(0, weight=1)

            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}   {label}",
                font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
                fg_color="transparent",
                hover_color=Colors.PRIMARY_HOVER,
                text_color=Colors.TEXT_LIGHT,
                anchor="w",
                corner_radius=Radius.SM,
                height=38,
                command=lambda k=key: self._select(k),
            )
            btn.grid(row=0, column=0, sticky="ew")
            self._buttons[key] = btn

            badge = ctk.CTkLabel(
                nav_frame, text="", width=20,
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
                text_color=Colors.TEXT_LIGHT,
                fg_color=Colors.TEXT_DANGER, corner_radius=Radius.SM,
            )
            badge.grid(row=0, column=1, padx=(Spacing.XS, Spacing.SM))
            badge.grid_remove()
            self._badges[key] = badge

        self.grid_rowconfigure(2 + len(self.NAV_ITEMS), weight=1)

        footer_row = 2 + len(self.NAV_ITEMS) + 1

        sep2 = ctk.CTkFrame(self, fg_color=Colors.BORDER, height=1)
        sep2.grid(row=footer_row, column=0, sticky="ew", padx=Spacing.MD, pady=(0, Spacing.SM))

        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.grid(row=footer_row + 1, column=0, sticky="ew",
                        padx=Spacing.MD, pady=(0, Spacing.SM))

        ctk.CTkLabel(
            mode_frame, text="Theme",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
        ).pack(side="left")

        mode_switch = ctk.CTkSwitch(
            mode_frame, text="",
            fg_color=Colors.BG_INPUT, progress_color=Colors.PRIMARY,
            button_color=Colors.TEXT_LIGHT, button_hover_color=Colors.PRIMARY_DARK,
            command=self._toggle_theme, width=36,
        )
        mode_switch.pack(side="right")
        self._mode_switch = mode_switch

        try:
            self._mode_switch.select() if str(ctk.get_appearance_mode()).lower() == "dark" else self._mode_switch.deselect()
        except Exception:
            pass

        ctk.CTkLabel(
            self, text="v2.0.0  |  Nepal",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
            text_color=Colors.TEXT_MUTED,
        ).grid(row=footer_row + 2, column=0, pady=(0, Spacing.SM))

        logout_btn = ctk.CTkButton(
            self, text="Logout",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            fg_color=Colors.ERROR, hover_color="#E01E5E",
            text_color="#FFFFFF",
            corner_radius=Radius.SM,
            height=34,
            command=self._logout,
        )
        logout_btn.grid(row=footer_row + 3, column=0, sticky="ew", padx=Spacing.SM, pady=(Spacing.SM, Spacing.LG))

        self._highlight(self._active)
        self._update_badges()


    # Handel logout
    def _logout(self) -> None:
        """Handle logout action."""
        if self._on_logout:
            self._on_logout()


    # Handle select
    def _select(self, key: str) -> None:
        self._active = key
        self._highlight(key)
        self._on_select(key)

    # Handle highlight
    def _highlight(self, active_key: str) -> None:
        for key, btn in self._buttons.items():
            is_active = (key == active_key)
            btn.configure(fg_color=(Colors.PRIMARY_DARK if is_active else "transparent"))


    # Handle update badges
    def _update_badges(self) -> None:
        """Refresh notification badges periodically (dashboard shows overdue count)."""
        try:
            overdue = len(db.get_overdue_plants()) if hasattr(db, "get_overdue_plants") else 0
            badge = self._badges.get("dashboard")
            if badge:
                if overdue > 0:
                    badge.configure(text=str(overdue))
                    badge.grid()
                else:
                    badge.grid_remove()
        except Exception:
            pass
        finally:
            self.after(30000, self._update_badges)

    # Apply theme to app
    def _apply_theme_to_app(self) -> None:
        """Best-effort refresh of key containers so theme toggle feels instant."""
        try:
            self.configure(fg_color=Colors.BG_CARD)
        except Exception:
            pass

        try:
            root = self.winfo_toplevel()
            root.configure(fg_color=Colors.BG_DARK)
        except Exception:
            pass

        try:
            root = self.winfo_toplevel()
            if hasattr(root, "_content"):
                root._content.configure(fg_color=Colors.BG_DARK)
            if hasattr(root, "_root_container"):
                try:
                    root._root_container.configure(
                        fg_color=Colors.BG_DARK if str(ctk.get_appearance_mode()).lower() == "dark" else Colors.BG_LIGHT
                    )
                except Exception:
                    pass
        except Exception:
            pass

        try:
            root = self.winfo_toplevel()
            frames = getattr(root, "_frames", None)
            if isinstance(frames, dict):
                for f in frames.values():
                    if hasattr(f, "refresh"):
                        try:
                            f.refresh()
                        except Exception:
                            pass
        except Exception:
            pass

    # Toggle theme
    def _toggle_theme(self):
        """Toggle light/dark and persist preference."""
        try:
            current = str(ctk.get_appearance_mode()).lower()
            new = "light" if current == "dark" else "dark"

            ctk.set_appearance_mode(new)

            try:
                from theme import apply_theme
                apply_theme(new)
            except Exception:
                pass

            try:
                self._mode_switch.select() if new == "dark" else self._mode_switch.deselect()
            except Exception:
                pass

            try:
                cur_user = db.get_current_user()
                if cur_user and cur_user.get("id"):
                    db.update_user_theme_pref(cur_user["id"], new)
            except Exception:
                pass

            self._apply_theme_to_app()

        except Exception:
            return