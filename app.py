"""
app.py  Main application window for Karesabari.

Orchestrates the sidebar, all content frames, and cross-frame communication.
"""

from __future__ import annotations

import customtkinter as ctk
from PIL import Image
from customtkinter import CTkImage
from theme import Colors, apply_theme, Spacing
import os
from window_config import get_window_size, DEFAULT_WINDOW_SIZE
import database as db
from sidebar import Sidebar
from dashboard import DashboardFrame
from ai_lab import AILabFrame
from catalogue import CatalogueFrame
from dev_panel import DevPanelFrame
from splash import SplashScreen
from login import LoginScreen
from notifications import NotificationCenter
from settings import SettingsFrame


class KaresabariApp(ctk.CTk):
    """Root application window with sidebar navigation."""

    APP_TITLE = "Karesabari  Kitchen Garden Manager"

    # Set up this object and prepare its initial state
    def __init__(self, window_preset: str = None):
        ctk.set_appearance_mode("dark")

        super().__init__()

        apply_theme()

        window_preset = (os.environ.get("KARESABARI_WINDOW") or 
                        window_preset or 
                        DEFAULT_WINDOW_SIZE)
        
        self.MIN_WIDTH, self.MIN_HEIGHT = get_window_size(window_preset)
        self._current_preset = window_preset

        self.title(self.APP_TITLE)
        self.geometry(f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}")
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        ctk.set_appearance_mode("light")
        apply_theme("light")
        ctk.set_default_color_theme("green")
        self.configure(fg_color=Colors.BG_LIGHT)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._root_container = ctk.CTkFrame(self, fg_color=Colors.BG_LIGHT, corner_radius=0)
        self._root_container.grid(row=0, column=0, sticky="nsew")
        self._root_container.grid_columnconfigure(0, weight=1)
        self._root_container.grid_rowconfigure(0, weight=1)

        self._corner_icon_ref: CTkImage | None = None
        self._corner_icon_label: ctk.CTkLabel | None = None

        self._show_splash()

        self._notifier: NotificationCenter | None = None


    # Update auth layout
    def _set_auth_layout(self) -> None:
        self.grid_columnconfigure(0, minsize=0, weight=1)
        self.grid_columnconfigure(1, minsize=0, weight=0)
        self.grid_rowconfigure(0, weight=1)

    # Show splash
    def _show_splash(self) -> None:
        self._hide_corner_icon()
        self._set_auth_layout()
        for w in self._root_container.winfo_children():
            w.destroy()
        self._splash = SplashScreen(self._root_container, on_complete=self._on_splash_done)
        self._splash.grid(row=0, column=0, sticky="nsew")
        self._splash.start_animation()

    # React when splash done
    def _on_splash_done(self) -> None:
        db.init_db()
        self._show_login()

    # Show login
    def _show_login(self) -> None:
        self._hide_corner_icon()
        self._set_auth_layout()
        for w in self._root_container.winfo_children():
            w.destroy()
        self._login = LoginScreen(self._root_container, on_login_success=self._on_login_success)
        self._login.grid(row=0, column=0, sticky="nsew")

    # Show corner icon
    def _show_corner_icon(self) -> None:
        icon_path = os.path.join(os.path.dirname(__file__), "logo", "icon.png")
        if not os.path.exists(icon_path):
            return
        if self._corner_icon_label is not None and self._corner_icon_label.winfo_exists():
            self._corner_icon_label.lift()
            return
        try:
            with Image.open(icon_path) as img:
                icon_img = img.convert("RGBA")
            self._corner_icon_ref = CTkImage(icon_img, size=(260, 220))
            self._corner_icon_label = ctk.CTkLabel(self, text="", image=self._corner_icon_ref)
            self._corner_icon_label.place(x=12, y=10)
            self._corner_icon_label.lift()
        except Exception:
            self._corner_icon_ref = None
            self._corner_icon_label = None

    # Hide corner icon
    def _hide_corner_icon(self) -> None:
        if self._corner_icon_label is not None:
            try:
                self._corner_icon_label.destroy()
            except Exception:
                pass
        self._corner_icon_label = None
        self._corner_icon_ref = None

    # React when login success
    def _on_login_success(self) -> None:
        for w in self._root_container.winfo_children():
            w.destroy()
        self._root_container.grid_remove()
        self._build_main_ui()

        try:
            if self._notifier is None:
                self._notifier = NotificationCenter(self)
            self._notifier.start()
        except Exception:
            pass

        user = db.get_current_user()
        if user:
            garden_id = user.get("garden_id") or user.get("family_id") or "Unknown"
            username = user.get("username", "User")
            self.title(f"garden {garden_id} : {username}")
            theme_pref = user.get("theme_pref") or "light"
            try:
                ctk.set_appearance_mode(theme_pref)
                apply_theme(theme_pref)
            except Exception:
                pass


    # Build main ui for this screen now
    def _build_main_ui(self) -> None:
        self.grid_columnconfigure(0, minsize=300, weight=0)  
        self.grid_columnconfigure(1, weight=1)  # main content takes remaining space
        self.grid_rowconfigure(0, weight=1)

        self._sidebar = Sidebar(self, on_select=self._navigate, on_logout=self._on_logout_requested)
        sidebar_height = max(420, self.MIN_HEIGHT - 120)
        self._sidebar.configure(width=300, height=sidebar_height)
        self._sidebar.grid_propagate(False)
        self._sidebar.grid(
            row=0, column=0, sticky="sw",
            padx=(0, 0),
            pady=(Spacing.XL, Spacing.MD)
        )
        self._show_corner_icon()

        self._content = ctk.CTkFrame(self, fg_color=Colors.BG_DARK, corner_radius=0)
        self._content.grid(
            row=0, column=1, sticky="nsew",
            padx=(0, 0),
            pady=Spacing.SM
        )
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._frames: dict[str, ctk.CTkFrame] = {}
        self._create_frames()
        self._show_frame("dashboard")

    # Create frames
    def _create_frames(self) -> None:
        self._frames["dashboard"] = DashboardFrame(
            self._content, on_navigate=self._handle_child_nav
        )
        self._frames["ai_lab"] = AILabFrame(self._content)
        self._frames["catalogue"] = CatalogueFrame(
            self._content, on_navigate=self._handle_child_nav
        )
        self._frames["settings"] = SettingsFrame(
            self._content, on_navigate=self._handle_child_nav
        )
        self._frames["dev_panel"] = DevPanelFrame(
            self._content, on_navigate=self._handle_child_nav
        )

        for frame in self._frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    # Show frame
    def _show_frame(self, key: str) -> None:
        if key == "garden":
            key = "dashboard"

        frame = self._frames.get(key)
        if frame:
            frame.tkraise()
            if hasattr(frame, "refresh"):
                frame.refresh()

    # Handle navigate
    def _navigate(self, key: str) -> None:
        self._show_frame(key)

    # React when logout requested
    def _on_logout_requested(self) -> None:
        """Handle logout: clear user session and return to login screen."""
        try:
            if self._notifier is not None:
                self._notifier.stop()
        except Exception:
            pass

        db.set_current_user(None)
        
        self.title(self.APP_TITLE)

        if hasattr(self, '_sidebar'):
            self._sidebar.destroy()
        if hasattr(self, '_content'):
            self._content.destroy()
        self._hide_corner_icon()

        self.grid_columnconfigure(0, minsize=0, weight=1)
        self.grid_columnconfigure(1, minsize=0, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self._root_container.grid(row=0, column=0, sticky="nsew")
            
        self._show_login()

    # Handel child nav
    def _handle_child_nav(self, action: str) -> None:
        """Handle cross-frame communication."""
        if action == "refresh_dashboard":
            dashboard = self._frames.get("dashboard")
            if dashboard and hasattr(dashboard, "refresh"):
                dashboard.refresh()
        elif action == "refresh_all":
            for frame in self._frames.values():
                if hasattr(frame, "refresh"):
                    frame.refresh()
        elif action == "go_garden":
            self._show_frame("dashboard")
            self._sidebar._select("dashboard")
        elif action == "go_settings":
            self._show_frame("settings")
            self._sidebar._select("settings")
