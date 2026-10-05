"""notifications.py

In-app popup notifications for Karesabari.

Goals:
- Show real pop-up notifications (inside app) for:
  - Family-scoped messages (notification pane / Activity Feed)
  - Overdue watering alerts
- Respect existing scoping rules: the current user only sees messages
  belonging to their family (and personal messages).

Implementation notes:
- Uses a lightweight CTkToplevel "toast" anchored to the top-right of the main window.
- Deduplicates notifications in-memory per launch using message ids.
"""

from __future__ import annotations

import customtkinter as ctk
from dataclasses import dataclass
from typing import Optional, Set

from theme import Colors, Fonts, Spacing, Radius
import database as db


@dataclass(frozen=True)
class NotificationItem:
    """A notification item derived from a DB message row."""

    id: int
    sender: str
    content: str
    msg_type: str
    created_at: str


class NotificationCenter:
    """Poll the DB for new messages and show toast popups."""

    # Set up this object and prepare its initial state
    def __init__(
        self,
        app: ctk.CTk,
        poll_ms: int = 1200,
        toast_duration_ms: int = 5500,
        limit: int = 10,
    ) -> None:
        self._app = app
        self._poll_ms = poll_ms
        self._toast_duration_ms = toast_duration_ms
        self._limit = limit

        self._seen_ids: Set[int] = set()
        self._after_id: Optional[str] = None

    # Handle start
    def start(self) -> None:
        self.stop()
        try:
            for m in db.get_messages(limit=self._limit, include_family=True):
                mid = m.get("id")
                if isinstance(mid, int):
                    self._seen_ids.add(mid)
        except Exception:
            pass

        self._schedule()

    # Handel stop
    def stop(self) -> None:
        if self._after_id is not None:
            try:
                self._app.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None

    # Handle schedule
    def _schedule(self) -> None:
        self._after_id = self._app.after(self._poll_ms, self._poll)

    # Handle poll
    def _poll(self) -> None:
        try:
            try:
                db.auto_update_statuses()
            except Exception:
                pass

            msgs = db.get_messages(limit=self._limit, include_family=True)
            for m in reversed(msgs):
                mid = m.get("id")
                if not isinstance(mid, int):
                    continue
                if mid in self._seen_ids:
                    continue
                self._seen_ids.add(mid)

                item = NotificationItem(
                    id=mid,
                    sender=str(m.get("sender") or "System"),
                    content=str(m.get("content") or ""),
                    msg_type=str(m.get("msg_type") or "info"),
                    created_at=str(m.get("created_at") or ""),
                )

                if item.content.strip():
                    try:
                        self._app.after(0, lambda it=item: self._show_toast(it))
                    except Exception:
                        pass

        finally:
            self._schedule()

    # Show toast
    def _show_toast(self, item: NotificationItem) -> None:
        """Show a small toast window top-right of the app."""

        accent = {
            "success": Colors.TEXT_SUCCESS,
            "warning": Colors.TEXT_WARNING,
            "error": Colors.TEXT_DANGER,
            "danger": Colors.TEXT_DANGER,
            "info": Colors.ACCENT_BLUE,
        }.get(item.msg_type, Colors.ACCENT_BLUE)

        toast = ctk.CTkToplevel(self._app)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)

        try:
            toast.update_idletasks()
        except Exception:
            pass

        bg = Colors.BG_CARD

        frame = ctk.CTkFrame(
            toast,
            fg_color=bg,
            corner_radius=Radius.LG,
            border_width=1,
            border_color=Colors.BORDER,
        )
        frame.pack(fill="both", expand=True)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        ctk.CTkLabel(
            header,
            text=item.sender,
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="•",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "bold"),
            text_color=accent,
        ).pack(side="right")

        ctk.CTkLabel(
            frame,
            text=item.content,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY),
            text_color=Colors.TEXT_SECONDARY,
            wraplength=320,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.MD))

        # Handle dismiss
        def dismiss(*_):
            try:
                toast.destroy()
            except Exception:
                pass

        toast.bind("<Button-1>", dismiss)
        frame.bind("<Button-1>", dismiss)

        # Handle place toast
        def _place_toast() -> None:
            try:
                self._app.update_idletasks()
                ax = self._app.winfo_rootx()
                ay = self._app.winfo_rooty()
                aw = self._app.winfo_width()

                width = 380
                height = 120
                x = ax + aw - width - 16
                y = ay + 16
                toast.geometry(f"{width}x{height}+{x}+{y}")
            except Exception:
                try:
                    toast.geometry("380x120")
                except Exception:
                    pass

        try:
            toast.after(0, _place_toast)
        except Exception:
            _place_toast()

        toast.after(self._toast_duration_ms, dismiss)
