import customtkinter as ctk
from theme import Colors
from PIL import Image
import os
import database as db



# Handle card
def _card(parent, width=720, height=700, corner_radius=20):
    frame = ctk.CTkFrame(parent, width=width, height=height, corner_radius=corner_radius, fg_color=Colors.BG_CARD)
    return frame


class LoginScreen(ctk.CTkFrame):
    # Set up this object and prepare its initial state
    def __init__(self, master, on_login_success):
        super().__init__(master, fg_color=Colors.BG_DARK)
        self.on_login_success = on_login_success
        try:
            db.init_db()
        except Exception:
            pass
        self._build_ui()

    # Build ui for this screen
    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.grid(row=0, column=0, padx=24, pady=24, sticky="nsew")
        shell.grid_columnconfigure(0, weight=3)
        shell.grid_columnconfigure(1, weight=2)
        shell.grid_rowconfigure(0, weight=1)

        card = _card(shell, width=720, height=700, corner_radius=18)
        card.grid(row=0, column=0, padx=(0, 16), pady=0, sticky="nsew")
        card.grid_propagate(True)
        card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, padx=44, pady=(28, 0), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        try:
            with Image.open(os.path.join("logo", "logo.png")) as _img:
                pil = _img.convert("RGBA").copy()
            self._login_logo = ctk.CTkImage(pil, size=(240, 120))
            ctk.CTkLabel(header, text="", image=self._login_logo).grid(row=0, column=0, pady=(0, 10))
        except Exception:
            pass

        ctk.CTkLabel(header, text="Welcome Back", font=ctk.CTkFont(size=22, weight="bold"), text_color=Colors.TEXT_PRIMARY).grid(row=1, column=0)
        ctk.CTkLabel(header, text="Sign in to your garden", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).grid(row=2, column=0, pady=(3, 0))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=1, column=0, padx=44, pady=(24, 0), sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="USERNAME", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_MUTED).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.user_entry = ctk.CTkEntry(form, height=44, corner_radius=10, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, placeholder_text="Enter username", placeholder_text_color=Colors.TEXT_MUTED, font=ctk.CTkFont(size=13))
        self.user_entry.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self.user_entry.bind("<Return>", lambda _e: self.pass_entry.focus())

        ctk.CTkLabel(form, text="PASSWORD", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_MUTED).grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.pass_entry = ctk.CTkEntry(form, height=44, corner_radius=10, show="*", fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, placeholder_text="Enter password", placeholder_text_color=Colors.TEXT_MUTED, font=ctk.CTkFont(size=13))
        self.pass_entry.grid(row=3, column=0, sticky="ew")
        self.pass_entry.bind("<Return>", lambda _e: self._login())

        self.show_pass_var = ctk.BooleanVar()
        ctk.CTkCheckBox(form, text="Show password", variable=self.show_pass_var, command=self._toggle_password, fg_color=Colors.PRIMARY, text_color=Colors.TEXT_PRIMARY).grid(row=4, column=0, sticky="w", pady=(5, 0))

        self.err_label = ctk.CTkLabel(form, text="", text_color=Colors.ERROR, font=ctk.CTkFont(size=11))
        self.err_label.grid(row=5, column=0, sticky="w", pady=(10, 0))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=2, column=0, padx=44, pady=(18, 0), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(actions, text="Sign In", height=46, corner_radius=10, fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER, text_color="#FFFFFF", font=ctk.CTkFont(size=15, weight="bold"), command=self._login).grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(actions, text="Create account", height=46, corner_radius=10, fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER, text_color="#FFFFFF", font=ctk.CTkFont(size=15, weight="bold"), command=self._open_signup).grid(row=1, column=0, sticky="ew", pady=(8, 0))

        ctk.CTkLabel(card, text="Karesabari  v2.0", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_MUTED).grid(row=3, column=0, pady=(16, 22))

        self._right_panel = ctk.CTkFrame(shell, fg_color=Colors.BG_INPUT, corner_radius=18, border_width=1, border_color=Colors.BORDER)
        self._right_panel.grid(row=0, column=1, sticky="nsew")
        self._right_panel.grid_rowconfigure(0, weight=1)
        self._right_panel.grid_columnconfigure(0, weight=1)

        self._icon_holder = ctk.CTkFrame(self._right_panel, fg_color="transparent")
        self._icon_holder.grid(row=0, column=0, sticky="nsew")
        self._icon_holder.grid_rowconfigure(0, weight=1)
        self._icon_holder.grid_columnconfigure(0, weight=1)

        try:
            with Image.open(os.path.join("logo", "icon.png")) as _img:
                pil = _img.convert("RGBA").copy()
            self._side_icon = ctk.CTkImage(pil, size=(320, 320))
            self._icon_label = ctk.CTkLabel(self._icon_holder, text="", image=self._side_icon)
            self._icon_label.grid(row=0, column=0)
        except Exception:
            self._icon_label = ctk.CTkLabel(
                self._icon_holder,
                text="icon.png not found",
                text_color=Colors.TEXT_MUTED,
                font=ctk.CTkFont(size=12),
            )
            self._icon_label.grid(row=0, column=0)

        self._signup_overlay = None

    # Handle login
    def _login(self):
        username = (self.user_entry.get() or "").strip()
        password = (self.pass_entry.get() or "").strip()
        ok, msg, user = db.authenticate(username, password)
        if ok and user:
            db.set_current_user(user)
            self.on_login_success()
        else:
            self.err_label.configure(text=msg)

    # Toggle password
    def _toggle_password(self):
        self.pass_entry.configure(show="" if self.show_pass_var.get() else "*")

    # Open signup
    def _open_signup(self):
        if self._signup_overlay is not None and self._signup_overlay.winfo_exists():
            return

        try:
            self._icon_holder.grid_remove()
        except Exception:
            pass

        self._signup_overlay = _SignUpOverlay(
            self._right_panel,
            on_created=self._on_signup_created,
            on_close=self._close_signup_overlay,
        )
        self._signup_overlay.grid(row=0, column=0, sticky="nsew")

    # Close signup overlay
    def _close_signup_overlay(self) -> None:
        if self._signup_overlay is not None:
            try:
                self._signup_overlay.destroy()
            except Exception:
                pass
        self._signup_overlay = None
        try:
            self._icon_holder.grid()
        except Exception:
            pass

    # React when signup created
    def _on_signup_created(self, user: dict) -> None:
        self._close_signup_overlay()
        db.set_current_user(user)
        self.on_login_success()


class _SignUpOverlay(ctk.CTkFrame):
    """Modular sign-up experience: create, join, or accept invite."""

    MODE_CREATE = "Create Garden"
    MODE_JOIN = "Join by ID"
    MODE_INVITE = "Use Invite"

    # Set up this object and prepare its initial state
    def __init__(self, parent, on_created=None, on_close=None):
        super().__init__(parent, fg_color=Colors.BG_CARD)
        self.created_user = None
        self._on_created = on_created
        self._on_close = on_close

        self._logo_image = None
        self._selected_invite_id = None
        self._pending_invites = []

        self._mode_var = ctk.StringVar(value=self.MODE_CREATE)
        self.show_pass_var = ctk.BooleanVar(value=False)

        self._build_ui()
        self._sync_mode()
        self.bind("<Return>", lambda _e: self._create())
        self.bind("<Escape>", lambda _e: self._request_close())

    # Build ui for this screen
    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        shell = ctk.CTkFrame(self, fg_color=Colors.BG_INPUT, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        shell.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        shell.grid_rowconfigure(1, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(shell, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Create an account",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Colors.PRIMARY_DARK,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Create a garden, join by ID, or accept invite.",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w")

        self._scroll_body = ctk.CTkScrollableFrame(
            shell,
            fg_color="transparent",
            corner_radius=0,
        )
        self._scroll_body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self._scroll_body.grid_columnconfigure(0, weight=1)

        self._build_account_section(self._scroll_body)
        self._build_mode_section(self._scroll_body)
        self._build_invite_inbox(self._scroll_body)
        self._build_action_section(shell)

    # Build account section for this screen
    def _build_account_section(self, parent) -> None:
        section = ctk.CTkFrame(parent, fg_color=Colors.BG_INPUT, corner_radius=14, border_width=1, border_color=Colors.BORDER)
        section.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            section,
            text="Account Details",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Colors.ACCENT_BLUE,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 8))

        self._username = ctk.CTkEntry(
            section,
            placeholder_text="Username",
            fg_color=Colors.BG_CARD,
            border_color=Colors.BORDER,
            height=38,
        )
        self._username.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        self._username.bind("<KeyRelease>", self._on_username_change)

        self._password = ctk.CTkEntry(
            section,
            placeholder_text="Password",
            show="*",
            fg_color=Colors.BG_CARD,
            border_color=Colors.BORDER,
            height=38,
        )
        self._password.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))

        self._confirm_password = ctk.CTkEntry(
            section,
            placeholder_text="Confirm password",
            show="*",
            fg_color=Colors.BG_CARD,
            border_color=Colors.BORDER,
            height=38,
        )
        self._confirm_password.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 8))

        ctk.CTkCheckBox(
            section,
            text="Show passwords",
            variable=self.show_pass_var,
            command=self._toggle_password,
            fg_color=Colors.PRIMARY,
            text_color=Colors.TEXT_PRIMARY,
        ).grid(row=4, column=0, sticky="w", padx=14, pady=(0, 12))

    # Build mode section for this screen
    def _build_mode_section(self, parent) -> None:
        section = ctk.CTkFrame(parent, fg_color=Colors.BG_INPUT, corner_radius=14, border_width=1, border_color=Colors.BORDER)
        section.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            section,
            text="Garden Onboarding",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Colors.ACCENT_ORANGE,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 8))

        self._mode = ctk.CTkSegmentedButton(
            section,
            values=[self.MODE_CREATE, self.MODE_JOIN, self.MODE_INVITE],
            variable=self._mode_var,
            command=lambda _v: self._sync_mode(),
            fg_color=Colors.BG_CARD,
            selected_color=Colors.PRIMARY,
            selected_hover_color=Colors.PRIMARY_HOVER,
        )
        self._mode.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        self._mode_hint = ctk.CTkLabel(
            section,
            text="Create a fresh garden and become its first member.",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
            justify="left",
        )
        self._mode_hint.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 8))

        self._mode_stack = ctk.CTkFrame(section, fg_color="transparent")
        self._mode_stack.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))
        self._mode_stack.grid_columnconfigure(0, weight=1)

        self._create_panel = ctk.CTkFrame(self._mode_stack, fg_color="transparent")
        self._create_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._create_panel, text="Garden name", text_color=Colors.TEXT_MUTED).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._garden_name = ctk.CTkEntry(
            self._create_panel,
            placeholder_text="My Garden",
            fg_color=Colors.BG_CARD,
            border_color=Colors.BORDER,
            height=36,
        )
        self._garden_name.grid(row=1, column=0, sticky="ew")

        self._join_panel = ctk.CTkFrame(self._mode_stack, fg_color="transparent")
        self._join_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._join_panel, text="6-digit Garden ID", text_color=Colors.TEXT_MUTED).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._garden_id = ctk.CTkEntry(
            self._join_panel,
            placeholder_text="e.g. 123456",
            fg_color=Colors.BG_CARD,
            border_color=Colors.BORDER,
            height=36,
        )
        self._garden_id.grid(row=1, column=0, sticky="ew")

        self._invite_panel = ctk.CTkFrame(self._mode_stack, fg_color="transparent")
        self._invite_panel.grid_columnconfigure(0, weight=1)
        self._invite_choice = ctk.CTkLabel(
            self._invite_panel,
            text="No invite selected. Use the Invite Inbox on the right.",
            text_color=Colors.TEXT_MUTED,
            justify="left",
        )
        self._invite_choice.grid(row=0, column=0, sticky="w")

    # Build action section for this screen
    def _build_action_section(self, parent) -> None:
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.grid(row=2, column=0, sticky="ew")
        section.grid_columnconfigure(0, weight=1)

        self._status = ctk.CTkLabel(section, text="", text_color=Colors.ERROR, justify="left")
        self._status.grid(row=0, column=0, sticky="w", pady=(0, 8))

        ctk.CTkLabel(
            section,
            text="Tip: Use the same username when checking invites.",
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))

        action_row = ctk.CTkFrame(section, fg_color="transparent")
        action_row.grid(row=2, column=0, sticky="ew")
        action_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            action_row,
            text="Cancel",
            fg_color="#DCEBFF",
            hover_color="#C9DFFF",
            text_color=Colors.TEXT_DARK,
            command=self._request_close,
            width=110,
        ).grid(row=0, column=0, sticky="w")

        self._create_btn = ctk.CTkButton(
            action_row,
            text="Create Account",
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            command=self._create,
            width=150,
        )
        self._create_btn.grid(row=0, column=1, sticky="e")

    # Build invite inbox for this screen
    def _build_invite_inbox(self, parent) -> None:
        ctk.CTkLabel(
            parent,
            text="Invite Inbox",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Colors.PRIMARY_DARK,
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(4, 6))

        hint = ctk.CTkLabel(
            parent,
            text="Type your username on the left, then fetch pending invites for that identity.",
            text_color=Colors.TEXT_MUTED,
            justify="left",
            wraplength=520,
        )
        hint.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 8))

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 8))
        btn_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_row,
            text="Check Invites",
            fg_color=Colors.ACCENT_BLUE,
            hover_color="#5AB0F5",
            command=self._load_invites,
            height=32,
        ).grid(row=0, column=0, sticky="w")

        self._invite_count = ctk.CTkLabel(btn_row, text="", text_color=Colors.TEXT_MUTED)
        self._invite_count.grid(row=0, column=1, sticky="e")

        self._invite_list = ctk.CTkFrame(parent, fg_color="transparent")
        self._invite_list.grid(row=5, column=0, sticky="nsew", padx=14, pady=(0, 8))
        self._invite_list.grid_columnconfigure(0, weight=1)

        self._render_invites([])

    # React when username change
    def _on_username_change(self, _event=None) -> None:
        self._selected_invite_id = None
        if self._mode_var.get() == self.MODE_INVITE:
            self._invite_choice.configure(text="No invite selected. Use the Invite Inbox on the right.")

    # Handle sync mode
    def _sync_mode(self) -> None:
        for panel in (self._create_panel, self._join_panel, self._invite_panel):
            panel.grid_forget()

        mode = self._mode_var.get()
        if mode == self.MODE_JOIN:
            self._mode_hint.configure(text="Join an existing garden using its 6-digit Garden ID.")
            self._join_panel.grid(row=0, column=0, sticky="ew")
        elif mode == self.MODE_INVITE:
            self._mode_hint.configure(text="Accept a pending invite sent to your username.")
            self._invite_panel.grid(row=0, column=0, sticky="ew")
        else:
            self._mode_hint.configure(text="Create a fresh garden and become its first member.")
            self._create_panel.grid(row=0, column=0, sticky="ew")

    # Render invites
    def _render_invites(self, invites) -> None:
        for w in self._invite_list.winfo_children():
            w.destroy()

        self._pending_invites = list(invites or [])
        self._invite_count.configure(text=f"{len(self._pending_invites)} pending")

        if not self._pending_invites:
            ctk.CTkLabel(
                self._invite_list,
                text="No pending invites for this username.",
                text_color=Colors.TEXT_MUTED,
            ).grid(row=0, column=0, sticky="w", pady=8)
            return

        for idx, inv in enumerate(self._pending_invites):
            invite_id = inv.get("id")
            gid = str(inv.get("garden_id") or "")
            gname = str(inv.get("garden_name") or "Garden")
            invited_by = str(inv.get("invited_by_username") or "a member")

            is_selected = bool(invite_id == self._selected_invite_id)
            card = ctk.CTkFrame(
                self._invite_list,
                fg_color=Colors.BG_CARD,
                corner_radius=10,
                border_width=2 if is_selected else 1,
                border_color=Colors.PRIMARY if is_selected else Colors.BORDER,
            )
            card.grid(row=idx, column=0, sticky="ew", pady=(0, 8))
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                card,
                text=f"{gname} ({gid})",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=Colors.TEXT_PRIMARY,
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))

            ctk.CTkLabel(
                card,
                text=f"Invited by: {invited_by}",
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))

            ctk.CTkButton(
                card,
                text=("Selected" if is_selected else "Select Invite"),
                fg_color=(Colors.PRIMARY_DARK if is_selected else Colors.PRIMARY),
                hover_color=Colors.PRIMARY_HOVER,
                state=("disabled" if is_selected else "normal"),
                width=110,
                height=28,
                command=lambda iid=invite_id, n=gname, g=gid: self._select_invite(iid, n, g),
            ).grid(row=0, column=1, rowspan=2, padx=10, pady=8, sticky="e")

    # Handle select invite
    def _select_invite(self, invite_id, garden_name: str, garden_id: str) -> None:
        self._selected_invite_id = int(invite_id)
        self._mode_var.set(self.MODE_INVITE)
        self._sync_mode()
        self._invite_choice.configure(text=f"Selected: {garden_name} ({garden_id})")
        self._render_invites(self._pending_invites)

    # Load invites into this view
    def _load_invites(self) -> None:
        username = (self._username.get() or "").strip()
        if not username:
            self._set_status("Type username first, then check invites.", is_error=True)
            return

        try:
            invites = db.get_pending_invites(username)
        except Exception:
            invites = []

        self._render_invites(invites)
        if invites:
            self._set_status("Pending invites loaded.", is_error=False)
        else:
            self._set_status("No pending invites found for this username.", is_error=True)

    # Update status
    def _set_status(self, text: str, is_error: bool = True) -> None:
        self._status.configure(text=text, text_color=(Colors.ERROR if is_error else Colors.TEXT_SUCCESS))

    # Create the current data
    def _create(self):
        try:
            self._create_btn.configure(state="disabled", text="Creating...")
        except Exception:
            pass

        try:
            db.init_db()
        except Exception:
            pass

        u = (self._username.get() or "").strip()
        p = (self._password.get() or "").strip()
        p2 = (self._confirm_password.get() or "").strip()

        if not u or not p:
            self._set_status("Please enter username and password", is_error=True)
            self._create_btn.configure(state="normal", text="Create Account")
            return
        if len(u) < 3:
            self._set_status("Username must be at least 3 characters", is_error=True)
            self._create_btn.configure(state="normal", text="Create Account")
            return
        if " " in u:
            self._set_status("Username cannot contain spaces", is_error=True)
            self._create_btn.configure(state="normal", text="Create Account")
            return
        if len(p) < 4:
            self._set_status("Password must be at least 4 characters", is_error=True)
            self._create_btn.configure(state="normal", text="Create Account")
            return
        if p != p2:
            self._set_status("Passwords do not match", is_error=True)
            self._create_btn.configure(state="normal", text="Create Account")
            return

        mode = self._mode_var.get()
        garden_name = (self._garden_name.get() or "").strip() or "My Garden"
        garden_id = None
        invite_id = None

        if mode == self.MODE_JOIN:
            join_id = (self._garden_id.get() or "").strip()
            if not (join_id.isdigit() and len(join_id) == 6):
                self._set_status("Garden ID must be a 6-digit number", is_error=True)
                self._create_btn.configure(state="normal", text="Create Account")
                return
            garden_id = join_id
        elif mode == self.MODE_INVITE:
            if self._selected_invite_id is None:
                self._set_status("Select an invite from Invite Inbox", is_error=True)
                self._create_btn.configure(state="normal", text="Create Account")
                return
            invite_id = int(self._selected_invite_id)

        try:
            user = db.create_user(u, p, garden_name, garden_id=garden_id, invite_id=invite_id)
        except Exception as e:
            self._set_status(f"Create failed: {e}", is_error=True)
            self._create_btn.configure(state="normal", text="Create Account")
            return

        if not user:
            detail = ""
            try:
                detail = (db.get_last_auth_error() or "").strip()
            except Exception:
                detail = ""

            msg = "Could not create account"
            if mode == self.MODE_JOIN:
                msg = "Username exists or Garden ID not found"
            elif mode == self.MODE_INVITE:
                msg = "Invite invalid, expired, or does not match username"

            if detail:
                msg = f"{msg}: {detail}"

            self._set_status(msg, is_error=True)
            self._create_btn.configure(state="normal", text="Create Account")
            return

        self.created_user = user
        if callable(self._on_created):
            self._on_created(user)

    # Handle request close
    def _request_close(self) -> None:
        if callable(self._on_close):
            self._on_close()

    # Toggle password
    def _toggle_password(self):
        show_char = "" if self.show_pass_var.get() else "*"
        self._password.configure(show=show_char)
        self._confirm_password.configure(show=show_char)


