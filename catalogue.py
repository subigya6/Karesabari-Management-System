"""
catalogue.py  Vegetable Catalogue module for Karesabari.

This is a rebuilt, robust implementation that:
- Loads catalogue rows from the database
- Resolves image assets from `image_path`, `logo/<slug>.png`, or `logo/logo.png`
- Caches CTkImage objects to avoid re-opening files
- Falls back to an emoji placeholder when images are missing
- Keeps image refs to avoid CTk GC issues
"""
from __future__ import annotations

from typing import Callable, Optional
from customtkinter import CTkImage
from PIL import Image
import customtkinter as ctk 
import os
import database as db
from theme import Colors, Fonts, Spacing, Radius


class CatalogueFrame(ctk.CTkFrame):
    """Searchable vegetable catalogue with reliable image loading."""

    CARD_COLS = 2

    # Set up this object and prepare its initial state
    def __init__(
        self,
        master: ctk.CTkFrame,
        on_navigate: Optional[Callable] = None,
        on_item_selected: Optional[Callable[[dict], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_navigate = on_navigate
        self._on_item_selected = on_item_selected

        self._image_cache: dict[str, CTkImage] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        top.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            top, text="Vegetable Catalogue",
            font=(Fonts.FAMILY, Fonts.SIZE_TITLE, "bold"),
            text_color=Colors.PRIMARY_DARK, anchor="w",
        )
        title.grid(row=0, column=0, sticky="w")

        self._count_label = ctk.CTkLabel(
            top, text="",
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
        )
        self._count_label.grid(row=0, column=1)

        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=Spacing.LG, pady=(0, Spacing.SM))
        search_frame.grid_columnconfigure(0, weight=1)

        self._search = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by name, Nepali name, or season...",
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=Radius.SM, height=36,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY),
        )
        self._search.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.SM))
        self._search.bind("<KeyRelease>", lambda e: self._load_items(self._search.get().strip()))

        ctk.CTkButton(
            search_frame, text="Reset", width=70,
            fg_color="#DCFCE7", hover_color="#BBF7D0",
            text_color=Colors.TEXT_DARK,
            corner_radius=Radius.SM,
            command=self._reset_search,
        ).grid(row=0, column=1)

        chip_frame = ctk.CTkFrame(self, fg_color="transparent")
        chip_frame.grid(row=2, column=0, sticky="w", padx=Spacing.LG, pady=(0, Spacing.SM))

        self._season_var = ctk.StringVar(value="All")
        self._chips: list[ctk.CTkButton] = []
        seasons = ["All", "Summer", "Winter", "Monsoon"]
        for idx, season in enumerate(seasons):
            btn = ctk.CTkButton(
                chip_frame,
                text=season,
                width=80,
                height=28,
                corner_radius=Radius.SM,
                fg_color=Colors.BG_INPUT,
                hover_color=Colors.BUTTON_HOVER,
                text_color=Colors.TEXT_PRIMARY,
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                command=lambda s=season: self._filter_season(s),
            )
            btn.grid(row=0, column=idx, padx=(0 if idx == 0 else Spacing.XS, Spacing.XS))
            self._chips.append(btn)

        self._grid = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._grid.grid(row=3, column=0, sticky="nsew", padx=Spacing.LG, pady=Spacing.SM)
        for c in range(self.CARD_COLS):
            self._grid.grid_columnconfigure(c, weight=1)

        self._items: list[dict] = []
        self.refresh()

    # Reset search
    def _reset_search(self) -> None:
        self._search.delete(0, "end")
        self._season_var.set("All")
        self._update_chips()
        self.refresh()

    # Filter season
    def _filter_season(self, season: str) -> None:
        self._season_var.set(season)
        self._update_chips()
        q = "" if season == "All" else season
        self._load_items(q)

    # Handle update chips
    def _update_chips(self) -> None:
        """Highlight active season chip with primary color and readable text."""
        active = self._season_var.get()
        for btn in self._chips:
            if btn.cget("text") == active:
                btn.configure(
                    fg_color=Colors.PRIMARY,
                    hover_color=Colors.PRIMARY_HOVER,
                    text_color="white",
                )
            else:
                btn.configure(
                    fg_color=Colors.BG_INPUT,
                    hover_color=Colors.BUTTON_HOVER,
                    text_color=Colors.TEXT_PRIMARY,
                )

    # Refresh teh current data
    def refresh(self) -> None:
        self._load_items("")

    # Handle find icon path
    def _find_icon_path(self, item: dict) -> Optional[str]:
        """Resolve an image path for a catalogue item.

        Priority:
          1) Explicit image_path in DB if it exists
          2) logo/<slug>.png if that exists
          3) fallback to logo/logo.png (generic plant icon)
        """
        base_dir = os.path.dirname(__file__)
        explicit = (item.get("image_path") or "").strip() if item else ""
        if explicit:
            explicit_abs = explicit if os.path.isabs(explicit) else os.path.join(base_dir, explicit)
            if os.path.exists(explicit_abs):
                return explicit_abs

        logo_dir = os.path.join(base_dir, "logo")

        slug_source = (item or {}).get("slug") or (item or {}).get("name", "")
        slug = slug_source.strip().lower().replace(" ", "_") if slug_source else ""
        if slug:
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                slug_path = os.path.join(logo_dir, f"{slug}{ext}")
                if os.path.exists(slug_path):
                    return slug_path

            try:
                for name in os.listdir(logo_dir):
                    lower = name.lower()
                    if lower.startswith(slug) and lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                        return os.path.join(logo_dir, name)
            except OSError:
                pass

        generic = os.path.join(logo_dir, "logo.png")
        if os.path.exists(generic):
            return generic

        return None

    # Return ctk image
    def _get_ctk_image(self, path: str, size: tuple[int, int]) -> Optional[CTkImage]:
        """Open image as CTkImage with simple cache; uses generic icon if needed."""
        if not path:
            return None
        key = (path, size)
        if not hasattr(self, "_image_cache"):
            self._image_cache = {}
        if key in self._image_cache:
            return self._image_cache[key]
        try:
            with Image.open(path) as im:
                img = im.convert("RGBA").copy()
        except (FileNotFoundError, OSError):
            generic = self._find_icon_path({})
            if not generic:
                return None
            with Image.open(generic) as im:
                img = im.convert("RGBA").copy()
        ctk_img = CTkImage(img, size=size)
        self._image_cache[key] = ctk_img
        return ctk_img

    # Load items into this view
    def _load_items(self, query: str) -> None:
        for w in self._grid.winfo_children():
            w.destroy()

        self._items = db.search_catalogue(query)
        self._count_label.configure(text=f"{len(self._items)} varieties")

        garden_plants = db.get_all_plants()
        planted_names = {p["name"].lower() for p in garden_plants}

        if not self._items:
            msg = ctk.CTkLabel(
                self._grid,
                text="No vegetables found. Try a different search.",
                font=(Fonts.FAMILY, Fonts.SIZE_BODY),
                text_color=Colors.TEXT_MUTED,
            )
            msg.grid(row=0, column=0, padx=Spacing.LG, pady=Spacing.LG)
            return

        for idx, item in enumerate(self._items):
            row = idx // self.CARD_COLS
            col = idx % self.CARD_COLS
            already = item["name"].lower() in planted_names
            self._create_catalogue_card(row, col, item, already)

    # Create catalogue card
    def _create_catalogue_card(self, row: int, col: int, item: dict, already_planted: bool) -> None:
        """Create a sleek, informative, click-to-add catalogue card."""
        card = ctk.CTkFrame(
            self._grid,
            fg_color=Colors.BG_CARD,
            corner_radius=Radius.LG,
            border_width=1,
            border_color=Colors.BORDER,
        )
        card.grid(row=row, column=col, padx=Spacing.SM, pady=Spacing.SM, sticky="nsew")
        card.grid_columnconfigure(1, weight=1)

        # React when pick
        def _on_pick(_e=None, it=item):
            if self._on_item_selected:
                self._on_item_selected(it)
            else:
                self._plant_from_catalogue(it)

        # Handle bind pick
        def _bind_pick(widget: ctk.CTkBaseClass) -> None:
            widget.bind("<Button-1>", _on_pick)
            try:
                widget.configure(cursor="hand2")
            except Exception:
                pass

        icon_path = self._find_icon_path(item)
        if icon_path:
            tk_img = self._get_ctk_image(icon_path, (72, 72))
            if tk_img:
                icon = ctk.CTkLabel(card, image=tk_img, text="", width=72, height=72)
                icon._img_ref = tk_img
                icon.grid(row=0, column=0, rowspan=2, padx=Spacing.MD, pady=Spacing.MD, sticky="n")
            else:
                icon = ctk.CTkLabel(card, text="🌱", width=72, height=72, corner_radius=36, fg_color=Colors.PRIMARY_DARK, text_color=Colors.TEXT_LIGHT, font=(Fonts.FAMILY, 22, "bold"))
                icon.grid(row=0, column=0, rowspan=2, padx=Spacing.MD, pady=Spacing.MD, sticky="n")
        else:
            icon = ctk.CTkLabel(card, text="🌱", width=72, height=72, corner_radius=36, fg_color=Colors.PRIMARY_DARK, text_color=Colors.TEXT_LIGHT, font=(Fonts.FAMILY, 22, "bold"))
            icon.grid(row=0, column=0, rowspan=2, padx=Spacing.MD, pady=Spacing.MD, sticky="n")

        title = item.get("name", "")
        ctk.CTkLabel(
            card,
            text=title,
            font=(Fonts.FAMILY, Fonts.SIZE_BODY, "bold"),
            text_color=Colors.TEXT_LIGHT,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(0, Spacing.MD), pady=(Spacing.MD, 0))

        nep = item.get("name_nepali") or ""
        if nep:
            ctk.CTkLabel(
                card,
                text=f"{nep}",
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
                text_color=Colors.ACCENT_ORANGE,
                anchor="w",
            ).grid(row=1, column=1, sticky="ew", padx=(0, Spacing.MD), pady=(2, 0))

        sci = item.get("scientific_name") or ""
        if sci:
            ctk.CTkLabel(
                card,
                text=sci,
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "italic"),
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).grid(row=2, column=1, sticky="ew", padx=(0, Spacing.MD), pady=(2, 0))

        freq = item.get("water_freq_hours", 24)
        season = item.get("season", "All")
        water_need = item.get("water_need", "medium")
        desc = item.get("description") or "No description available."
        meta = f"Season: {season}  |  Water: {water_need}  |  Every {int(freq)}h"

        ctk.CTkLabel(
            card,
            text=desc,
            font=(Fonts.FAMILY, Fonts.SIZE_SMALL),
            text_color=Colors.TEXT_MUTED,
            wraplength=260,
            justify="left",
            anchor="w",
        ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=Spacing.MD, pady=(Spacing.XS, 0))

        meta_wrap = ctk.CTkFrame(card, fg_color="transparent")
        meta_wrap.grid(row=4, column=0, columnspan=2, sticky="ew", padx=Spacing.MD, pady=(Spacing.XS, Spacing.MD))

        ctk.CTkLabel(
            meta_wrap,
            text=f"Season: {season}",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left")
        ctk.CTkLabel(
            meta_wrap,
            text=f"Water: {water_need}",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left", padx=(Spacing.MD, 0))
        ctk.CTkLabel(
            meta_wrap,
            text=f"Every {int(freq)}h",
            font=(Fonts.FAMILY, Fonts.SIZE_CAPTION),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left", padx=(Spacing.MD, 0))

        if already_planted:
            ctk.CTkLabel(
                meta_wrap,
                text="IN GARDEN",
                fg_color=Colors.EARTH_LIGHT,
                text_color=Colors.TEXT_LIGHT,
                corner_radius=Radius.SM,
                font=(Fonts.FAMILY, Fonts.SIZE_CAPTION, "bold"),
                padx=Spacing.SM,
                pady=2,
            ).pack(side="right")

        _bind_pick(card)
        for child in card.winfo_children():
            _bind_pick(child)

    # Handle plant from catalogue
    def _plant_from_catalogue(self, item: dict) -> None:
        pid = db.add_plant_from_catalogue(item["id"], "")
        if pid:
            db.add_message(f"'{item['name']}' planted from catalogue!", "Catalogue", "success")
            if self._on_navigate:
                self._on_navigate("garden")
                
    # Create item card now
    def _create_item_card(self, row: int, col: int, item: dict) -> None:
        
        name_frame = ctk.CTkFrame(card, fg_color="transparent")
        name_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=Spacing.MD, pady=Spacing.XS)
        
        ctk.CTkLabel(
            name_frame, text=item["name"],
            font=(Fonts.FAMILY, Fonts.SIZE_HEADING, "bold"),
            text_color=Colors.TEXT_LIGHT, anchor="w",
        ).pack(side="left")

        if item.get("name_nepali"):
            ctk.CTkLabel(
                name_frame, text=f" ({item['name_nepali']})",
                font=(Fonts.FAMILY, Fonts.SIZE_BODY),
                text_color=Colors.ACCENT_ORANGE, anchor="w",
            ).pack(side="left", padx=Spacing.XS)

        if item.get("scientific_name"):
            ctk.CTkLabel(
                card, text=item["scientific_name"],
                font=(Fonts.FAMILY, Fonts.SIZE_SMALL, "italic"),
                text_color=Colors.TEXT_MUTED, anchor="w",
            ).grid(row=2, column=0, columnspan=2, sticky="w", padx=Spacing.MD)

    # Delete from catalogue
    def _delete_from_catalogue(self, item: dict) -> None:
        """Remove a vegetable from the catalogue DB and refresh the list.

        The corresponding card will disappear after refresh. Items that are
        currently used in the garden (plants table) are protected.
        """
        item_id = item.get("id") or item.get("catalogue_id")
        if not item_id:
            return

        try:
            plants = db.get_all_plants()
            if any(p.get("catalogue_id") == item_id for p in plants):
                try:
                    db.add_message(
                        f"Cannot delete '{item.get('name', 'item')}' because it is used in the garden.",
                        sender="System",
                        msg_type="warning",
                    )
                except TypeError:
                    db.add_message(
                        f"Cannot delete '{item.get('name', 'item')}' because it is used in the garden.",
                        "System",
                        "warning",
                    )
                return
        except Exception:
            return

        try:
            if hasattr(db, "delete_catalogue_item"):
                db.delete_catalogue_item(item_id)
            else:
                conn = db._connect()  # type: ignore[attr-defined]
                with conn:
                    conn.execute("DELETE FROM catalogue WHERE id = ?", (item_id,))
                conn.close()
        except Exception:
            return

        self.refresh()
