"""settings.py — Settings panel for Karesabari.

Shows:
  - Active Garden (6-digit garden_id)
  - Members in the current garden
  - Gardens associated with the current user (and allows switching)

Backwards compatible with older DBs by relying on database.py helpers.
"""

from __future__ import annotations

from typing import Callable, Optional
import customtkinter as ctk

from theme import Colors, Fonts, Spacing, Radius
import database as db


class SettingsFrame(ctk.CTkFrame):
    """Settings / account and garden management."""

    # Set up this object and prepare its initial state
    def __init__(self, master: ctk.CTkFrame, on_navigate: Optional[Callable] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_navigate = on_navigate

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        hero = ctk.CTkFrame(
            self,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.LG,
            border_width=1,
            border_color=Colors.BORDER,
        )
        hero.grid(row=0, column=0, sticky="ew", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        hero.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hero,
            text="Settings & Garden Access",
            font=(Fonts.FAMILY, 24, "bold"),
            text_color=Colors.PRIMARY_DARK,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=Spacing.LG, pady=(Spacing.MD, 2))

        ctk.CTkLabel(
            hero,
            text="Manage your active garden, switch spaces, and invite members.",
            font=(Fonts.FAMILY, Fonts.SIZE_BODY),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=Spacing.LG, pady=(0, Spacing.MD))

        self._hero_badge = ctk.CTkLabel(
            hero,
            text="Not Signed In",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
            text_color=Colors.TEXT_DARK,
            fg_color=Colors.ACCENT_YELLOW,
            corner_radius=Radius.SM,
            padx=Spacing.SM,
            pady=2,
        )
        self._hero_badge.grid(row=0, column=1, rowspan=2, sticky="e", padx=Spacing.LG)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=1, column=0, sticky="ew", padx=Spacing.LG, pady=(0, Spacing.SM))
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=1)

        self._active_card = ctk.CTkFrame(top, fg_color=Colors.BG_CARD, corner_radius=Radius.LG, border_width=1, border_color=Colors.BORDER)
        self._active_card.grid(row=0, column=0, sticky="nsew", padx=(0, Spacing.SM))
        self._active_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._active_card,
            text="Active Garden",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.ACCENT_BLUE,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        ctk.CTkLabel(
            self._active_card,
            text="Share this ID with trusted members.",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.XS))

        gid_row = ctk.CTkFrame(self._active_card, fg_color="transparent")
        gid_row.grid(row=2, column=0, sticky="ew", padx=Spacing.MD)
        gid_row.grid_columnconfigure(0, weight=1)

        self._active_garden_entry = ctk.CTkEntry(
            gid_row,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
            height=34,
            font=(Fonts.FAMILY_MONO, 14, "bold"),
        )
        self._active_garden_entry.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))

        self._copy_btn = ctk.CTkButton(
            gid_row,
            text="Copy",
            width=80,
            height=34,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=Radius.SM,
            command=self._copy_garden_id,
        )
        self._copy_btn.grid(row=0, column=1, sticky="e")

        self._copy_status = ctk.CTkLabel(
            self._active_card,
            text="",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self._copy_status.grid(row=3, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.XS, 0))

        self._active_hint = ctk.CTkLabel(
            self._active_card,
            text="Shared with all members of this garden.",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self._active_hint.grid(row=4, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.XS, Spacing.MD))

        self._gardens_card = ctk.CTkFrame(top, fg_color=Colors.BG_CARD, corner_radius=Radius.LG, border_width=1, border_color=Colors.BORDER)
        self._gardens_card.grid(row=0, column=1, sticky="nsew", padx=(Spacing.SM, 0))
        self._gardens_card.grid_columnconfigure(0, weight=1)
        self._gardens_card.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self._gardens_card,
            text="My Gardens",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.ACCENT_ORANGE,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        self._gardens_meta = ctk.CTkLabel(
            self._gardens_card,
            text="",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self._gardens_meta.grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.XS))

        self._gardens_list = ctk.CTkScrollableFrame(self._gardens_card, fg_color="transparent", corner_radius=0, height=140)
        self._gardens_list.grid(row=2, column=0, sticky="nsew", padx=Spacing.MD, pady=(0, Spacing.MD))
        self._gardens_list.grid_columnconfigure(0, weight=1)

        self._members_card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Radius.LG, border_width=1, border_color=Colors.BORDER)
        self._members_card.grid(row=2, column=0, sticky="nsew", padx=Spacing.LG, pady=(0, Spacing.LG))
        self._members_card.grid_columnconfigure(0, weight=1)
        self._members_card.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            self._members_card,
            text="Garden Members",
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.PRIMARY_DARK,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        self._members_meta = ctk.CTkLabel(
            self._members_card,
            text="",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self._members_meta.grid(row=0, column=0, sticky="e", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        invite_row = ctk.CTkFrame(self._members_card, fg_color="transparent")
        invite_row.grid(row=1, column=0, sticky="ew", padx=Spacing.LG, pady=(0, Spacing.SM))
        invite_row.grid_columnconfigure(0, weight=1)

        self._invite_entry = ctk.CTkEntry(
            invite_row,
            placeholder_text="Invite by username (existing account)",
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=Radius.SM,
            height=34,
        )
        self._invite_entry.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.SM))
        self._invite_entry.bind("<Return>", lambda _e: self._invite_member())

        self._invite_btn = ctk.CTkButton(
            invite_row,
            text="Invite",
            width=90,
            height=34,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=Radius.SM,
            command=self._invite_member,
        )
        self._invite_btn.grid(row=0, column=1, sticky="e")

        self._invite_status = ctk.CTkLabel(
            self._members_card,
            text="",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self._invite_status.grid(row=2, column=0, sticky="w", padx=Spacing.LG, pady=(0, Spacing.XS))

        self._members_list = ctk.CTkScrollableFrame(self._members_card, fg_color="transparent", corner_radius=0)
        self._members_list.grid(row=3, column=0, sticky="nsew", padx=Spacing.LG, pady=(0, Spacing.LG))
        self._members_list.grid_columnconfigure(0, weight=1)

        self.refresh()

    # Update gid entry
    def _set_gid_entry(self, gid: str) -> None:
        try:
            self._active_garden_entry.configure(state="normal")
            self._active_garden_entry.delete(0, "end")
            self._active_garden_entry.insert(0, gid)
            self._active_garden_entry.configure(state="readonly")
        except Exception:
            pass

    # Copy garden id
    def _copy_garden_id(self) -> None:
        gid = ""
        try:
            gid = (self._active_garden_entry.get() or "").strip()
        except Exception:
            gid = ""

        if not gid or not (gid.isdigit() and len(gid) == 6):
            try:
                self._copy_status.configure(text="No valid Garden ID to copy")
            except Exception:
                pass
            return

        try:
            root = self.winfo_toplevel()
            root.clipboard_clear()
            root.clipboard_append(gid)
            root.update()  # keep on clipboard after app closes (best effort)
            self._copy_status.configure(text="Copied to clipboard")
            self.after(1800, lambda: self._copy_status.configure(text=""))
        except Exception:
            try:
                self._copy_status.configure(text="Copy failed")
            except Exception:
                pass

    # Refresh the current data
    def refresh(self) -> None:
        user = db.get_current_user() or {}
        gid = str(user.get("garden_id") or user.get("family_id") or "")

        try:
            if gid:
                self._hero_badge.configure(text=f"Garden {gid}", fg_color=Colors.ACCENT_YELLOW)
            else:
                self._hero_badge.configure(text="Not Signed In", fg_color=Colors.EARTH)
        except Exception:
            pass

        if not gid:
            self._set_gid_entry("")
            try:
                self._active_garden_entry.configure(placeholder_text="(not signed in)")
            except Exception:
                pass
            try:
                self._copy_btn.configure(state="disabled")
            except Exception:
                pass
        else:
            self._set_gid_entry(gid)
            try:
                self._active_garden_entry.configure(placeholder_text="")
            except Exception:
                pass
            try:
                self._copy_btn.configure(state="normal")
            except Exception:
                pass

        self._render_gardens()
        self._render_members(gid)

    # Render gardens
    def _render_gardens(self) -> None:
        for w in self._gardens_list.winfo_children():
            w.destroy()

        gardens = []
        try:
            gardens = db.get_user_gardens()
        except Exception:
            gardens = []

        if not gardens:
            try:
                self._gardens_meta.configure(text="0 linked gardens")
            except Exception:
                pass
            ctk.CTkLabel(
                self._gardens_list,
                text="No gardens found for this account.",
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            return

        try:
            self._gardens_meta.configure(text=f"{len(gardens)} linked garden(s)")
        except Exception:
            pass

        active_gid = str((db.get_current_user() or {}).get("garden_id") or "")

        for idx, g in enumerate(gardens):
            gid = str(g.get("garden_id") or "")
            name = str(g.get("name") or "Garden")

            row = ctk.CTkFrame(
                self._gardens_list,
                fg_color=Colors.BG_INPUT,
                corner_radius=Radius.MD,
                border_width=1,
                border_color=Colors.BORDER,
            )
            row.grid(row=idx, column=0, sticky="ew", pady=Spacing.XS)
            row.grid_columnconfigure(0, weight=1)

            title = f"{name}" if name else "Garden"
            ctk.CTkLabel(
                row,
                text=title,
                font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
                text_color=Colors.TEXT_LIGHT,
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.SM, 0))

            ctk.CTkLabel(
                row,
                text=(f"ID: {gid}" if gid else ""),
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.SM))

            if gid and gid == active_gid:
                ctk.CTkLabel(
                    row,
                    text="ACTIVE",
                    font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
                    text_color=Colors.TEXT_DARK,
                    fg_color=Colors.ACCENT_YELLOW,
                    corner_radius=Radius.SM,
                    padx=Spacing.SM,
                    pady=2,
                ).grid(row=0, column=1, sticky="e", padx=(0, Spacing.XS), pady=(Spacing.SM, 0))

            ctk.CTkButton(
                row,
                text=("Selected" if gid and gid == active_gid else "Switch"),
                state=("disabled" if gid and gid == active_gid else "normal"),
                fg_color=Colors.PRIMARY,
                hover_color=Colors.PRIMARY_HOVER,
                corner_radius=Radius.SM,
                height=28,
                width=90,
                command=lambda x=gid: self._switch_garden(x),
            ).grid(row=0, column=1, rowspan=2, padx=Spacing.MD, pady=Spacing.SM, sticky="e")

    # Render members
    def _render_members(self, gid: str) -> None:
        for w in self._members_list.winfo_children():
            w.destroy()

        if not gid:
            try:
                self._members_meta.configure(text="0 members")
            except Exception:
                pass
            ctk.CTkLabel(
                self._members_list,
                text="Sign in to view garden members.",
                font=(Fonts.FAMILY, Fonts.SIZE_BODY),
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            return

        try:
            members = db.get_garden_members(gid)
        except Exception:
            members = []

        if not members:
            try:
                self._members_meta.configure(text="0 members")
            except Exception:
                pass
            ctk.CTkLabel(
                self._members_list,
                text="No members found.",
                font=(Fonts.FAMILY, Fonts.SIZE_BODY),
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            return

        try:
            self._members_meta.configure(text=f"{len(members)} member(s)")
        except Exception:
            pass

        for idx, m in enumerate(members):
            row = ctk.CTkFrame(
                self._members_list,
                fg_color=Colors.BG_INPUT,
                corner_radius=Radius.MD,
                border_width=1,
                border_color=Colors.BORDER,
            )
            row.grid(row=idx, column=0, sticky="ew", pady=Spacing.XS)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row,
                text=str(m.get("username") or "user"),
                font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
                text_color=Colors.TEXT_LIGHT,
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=Spacing.MD, pady=(Spacing.SM, 0))

            ctk.CTkLabel(
                row,
                text=f"Garden ID: {m.get('garden_id', '')}",
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).grid(row=1, column=0, sticky="w", padx=Spacing.MD, pady=(0, Spacing.SM))

            if idx == 0:
                ctk.CTkLabel(
                    row,
                    text="OWNER",
                    font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
                    text_color=Colors.TEXT_DARK,
                    fg_color=Colors.ACCENT_YELLOW,
                    corner_radius=Radius.SM,
                    padx=Spacing.SM,
                    pady=2,
                ).grid(row=0, column=1, rowspan=2, sticky="e", padx=Spacing.MD, pady=Spacing.SM)

    # Switch garden
    def _switch_garden(self, gid: str) -> None:
        if not gid:
            return
        ok = False
        try:
            ok = db.switch_user_garden(gid)
        except Exception:
            ok = False

        if ok:
            try:
                db.add_message(f"Switched to garden {gid}", sender="Settings", msg_type="info")
            except Exception:
                pass
            self.refresh()
            if self._on_navigate:
                self._on_navigate("refresh_all")

    # Invite member
    def _invite_member(self) -> None:
        username = ""
        try:
            username = (self._invite_entry.get() or "").strip()
        except Exception:
            username = ""

        if not username:
            try:
                self._invite_status.configure(text="Enter a username", text_color=Colors.TEXT_WARNING)
            except Exception:
                pass
            return

        ok = False
        msg = "Invite failed"
        try:
            ok, msg = db.invite_user_to_garden(username)
        except Exception:
            ok, msg = False, "Invite failed"

        try:
            self._invite_status.configure(
                text=msg,
                text_color=(Colors.TEXT_SUCCESS if ok else Colors.TEXT_DANGER),
            )
        except Exception:
            pass

        if ok:
            try:
                self._invite_entry.delete(0, "end")
            except Exception:
                pass
            self.refresh()
            if self._on_navigate:
                self._on_navigate("refresh_all")
