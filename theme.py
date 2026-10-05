"""
theme.py — Nepal-centric color palette and styling constants for Karesabari.

Inspired by the lush greens of the Terai, the earthy browns of the Hills,
and the clean whites of the Himalayan peaks.
"""


class Colors:
    """Centralized color definitions."""

    PRIMARY        = "#22C55E"   # modern green (less neon than before)
    PRIMARY_HOVER  = "#34D399"   # softer mint hover
    PRIMARY_LIGHT  = "#86EFAC"   # light mint
    PRIMARY_DARK   = "#16A34A"   # deep green

    BG_DARK        = "#0B1220"   # deep navy
    BG_SIDEBAR     = "#0E1A2B"   # slightly elevated sidebar
    BG_CARD        = "#111F33"   # elevated card surface
    BG_INPUT       = "#0C1828"   # input fields

    ERROR          = "#FB4D7D"   # softer pink-red for errors
    WARNING        = "#FBBF24"   # warm amber for warnings
    SUCCESS        = "#2AE67D"

    TEXT_PRIMARY   = "#EAF2FF"   # cool white
    TEXT_SECONDARY = "#B6C2D1"   # muted slate
    TEXT_LIGHT     = "#EAF2FF"   # light text for dark mode
    TEXT_DARK      = "#111827"   # used in light mode
    TEXT_MUTED     = "#7D8CA3"   # softer muted for readability
    TEXT_SUCCESS   = "#2AE67D"   # success text color
    TEXT_WARNING   = "#FBBF24"   # warning text color
    TEXT_DANGER    = "#FF4D6D"   # danger text color

    ACCENT_ORANGE  = "#FF9F43"  # warmer, modern orange
    ACCENT_BLUE    = "#4CC9F0"  # neon-cyan blue
    ACCENT_YELLOW  = "#FBBF24"  # bright amber yellow

    BORDER         = "#24354A"   # clearer card separation

    SHADOW         = "#050A14"   # pseudo-shadow tone
    HIGHLIGHT      = "#1C2D47"   # top-edge highlight tone

    EARTH          = "#0F172A"  # deep slate for earthy elementa
    EARTH_LIGHT    = "#172554" # lighter slate for hover states
    EARTH_DARK     = "#070B14" # very dark slate for depth
    DARK_GREEN     = "#14532D" # rich dark green for accents and text

    BG_PRIMARY     = "#ECFDF3"  # light mint background for cards and highlights
    BG_LIGHT       = "#F3F4F6" # off-white for main backgrounds
    BG_LIGHT_CARD  = "#FFFFFF" # pure white for cards in light mode
    BG_LIGHT_SIDE  = "#ECFDF3" # light mint for sidebar in light mode

    BUTTON_HOVER   = "#E5E7EB" # light gray hover for buttons in light mode

    TRANSPARENT    = "transparent" #just transparent lol


class Fonts:
    """Font family and size presets."""

    FAMILY       = "Segoe UI"
    FAMILY_MONO  = "Consolas"

    SIZE_TITLE   = 22
    SIZE_HEADING = 16
    SIZE_BODY    = 14
    SIZE_SMALL   = 12
    SIZE_CAPTION = 11


class Spacing:
    """Consistent spacing scale (px)."""

    XS  = 4
    SM  = 8
    MD  = 12
    LG  = 16
    XL  = 24
    XXL = 32


class Radius:
    """Corner radius presets."""

    SM  = 8
    MD  = 12
    LG  = 16
    XL  = 22


# Apply theme
def apply_theme(mode: str = "dark") -> None:
    """Apply a light or dark theme by mutating the `Colors` class attributes.

    This updates the color constants so newly created widgets pick up
    the appropriate palette. Callers can also use this before
    rebuilding UI elements. Mode is case-insensitive and accepts
    'light' or 'dark'.
    """
    m = (mode or "dark").lower()

    if m == "light":
        Colors.BG_DARK = Colors.BG_LIGHT
        Colors.BG_SIDEBAR = Colors.BG_LIGHT_SIDE
        Colors.BG_CARD = Colors.BG_LIGHT_CARD
        Colors.BG_INPUT = "#F9FAFB" # very light gray for inputs in light mode

        Colors.TEXT_LIGHT = Colors.TEXT_DARK
        Colors.TEXT_PRIMARY = "#0F172A"      # deep slate
        Colors.TEXT_SECONDARY = "#4B5563"    # slate
        Colors.TEXT_MUTED = "#6B7280"     # softer muted slate for readability

        Colors.BORDER = "#E5E7EB"            # soft divider

        Colors.PRIMARY = "#16A34A"           # richer but not neon
        Colors.PRIMARY_DARK = "#15803D"     # darker green for hover and active states
        Colors.PRIMARY_HOVER = "#22C55E"     # hover state between primary and primary_dark

        Colors.ACCENT_BLUE = "#2563EB" # deeper blue for accents in light mode
        Colors.ACCENT_ORANGE = "#EA580C" # deeper orange for accents in light mode

        Colors.EARTH = "#E5E7EB"             # neutral card backgrounds / chips
        Colors.EARTH_LIGHT = "#DCFCE7"       # pale green hover or badges

        Colors.TEXT_SUCCESS = "#16A34A"     # success text color in light mode
        Colors.TEXT_WARNING = "#CA8A04"     # warning text color in light mode
        Colors.TEXT_DANGER = "#B91C1C"      # danger text color in light mode

        Colors.BUTTON_HOVER = "#E5E7EB" # light gray hover for buttons in light mode

        Colors.SHADOW = "#000000"          # stronger shadow for light mode
        Colors.HIGHLIGHT = "#E5E7EB"     # lighter highlight for light mode

    else:
        Colors.BG_DARK = "#0B1220"  # deep navy for main background
        Colors.BG_SIDEBAR = "#0C1A2A"   # slightly darker than cards
        Colors.BG_CARD = "#0F2136"      # a bit lighter than BG for elevation
        Colors.BG_INPUT = "#0B1B2D"     # input slightly darker than card

        Colors.TEXT_LIGHT = "#EAF2FF"  # light text for dark mode
        Colors.TEXT_MUTED = "#8CA0B8"   # slightly brighter muted for readability
        Colors.TEXT_PRIMARY = "#EAF2FF"     # light text for primary content in dark mode
        Colors.TEXT_SECONDARY = "#C4D1E3"  # brighter slate for secondary text in dark mode

        Colors.BORDER = "#243B55"       # clearer divider on new card tone

        Colors.PRIMARY = "#22C55E"      # modern green
        Colors.PRIMARY_HOVER = "#34D399" # softer mint hover
        Colors.PRIMARY_DARK = "#16A34A"     # darker green for hover and active states
        Colors.PRIMARY_DARK = "#86EFAC"    # light mint for hover state in dark mode

        Colors.ACCENT_BLUE = "#38BDF8"  # sky blue (less neon)
        Colors.ACCENT_ORANGE = "#FB923C"  # warm orange (less saturated)

        Colors.EARTH = "#0F172A"            # deep slate for earthy elements
        Colors.EARTH_LIGHT = "#172554"       # lighter slate for hover states on earthy elements

        Colors.TEXT_SUCCESS = "#22C55E"    # success text color in dark mode
        Colors.TEXT_WARNING = "#FBBF24"   # warning text color in dark mode
        Colors.TEXT_DANGER = "#FB7185"  # softer pink-red

        Colors.BUTTON_HOVER = "#17324B" # darker hover for buttons in dark mode

        Colors.SHADOW = "#050A14"         # subtle shadow for depth in dark mode
        Colors.HIGHLIGHT = "#16314A"    # subtle highlight for depth in dark mode
