"""
window_config.py — Window sizing presets and configuration for Karesabari.

Supports:
  - Phone sizes (iPhone, Android)
  - Tablet sizes
  - Desktop/Default
  - Custom scaling for testing
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WindowSize:
    """Window size preset."""
    name: str
    width: int
    height: int
    description: str


WINDOW_PRESETS: dict[str, WindowSize] = {
    "iPhone_SE": WindowSize("iPhone SE", 375, 812, "iPhone SE (2020)"),
    "iPhone_12": WindowSize("iPhone 12", 390, 844, "iPhone 12 / 13"),
    "iPhone_14": WindowSize("iPhone 14", 390, 844, "iPhone 14 / 15"),
    "iPhone_Pro": WindowSize("iPhone Pro Max", 428, 926, "iPhone 14/15 Pro Max"),
    "iPhone_8": WindowSize("iPhone 8", 375, 667, "iPhone 8 / SE (1st gen)"),
    
    "Pixel_5": WindowSize("Pixel 5", 393, 851, "Google Pixel 5"),
    "Pixel_6": WindowSize("Pixel 6", 412, 915, "Google Pixel 6"),
    "Samsung_S21": WindowSize("Galaxy S21", 360, 800, "Samsung Galaxy S21"),
    "Samsung_S22": WindowSize("Galaxy S22", 360, 800, "Samsung Galaxy S22"),
    
    "iPad_Mini": WindowSize("iPad Mini", 768, 1024, "iPad Mini"),
    "iPad_Air": WindowSize("iPad Air", 820, 1180, "iPad Air"),
    "iPad_Pro_11": WindowSize("iPad Pro 11", 834, 1194, "iPad Pro 11-inch"),
    
    "Desktop_1080p": WindowSize("Desktop 1080p", 1080, 720, "Default Desktop"),
    "Desktop_1440p": WindowSize("Desktop 1440p", 1440, 900, "1440p Monitor"),
    "Desktop_4K": WindowSize("Desktop 4K", 1920, 1200, "4K Monitor"),
}

DEFAULT_WINDOW_SIZE = "Desktop_1080p"
CURRENT_WINDOW_SIZE: Optional[str] = None


# Return window size
def get_window_size(preset_name: str = DEFAULT_WINDOW_SIZE) -> tuple[int, int]:
    """Get width and height from preset name."""
    if preset_name not in WINDOW_PRESETS:
        preset_name = DEFAULT_WINDOW_SIZE
    size = WINDOW_PRESETS[preset_name]
    return size.width, size.height


# Return all presets
def get_all_presets() -> dict[str, WindowSize]:
    """Get all available presets."""
    return WINDOW_PRESETS


# Return preset names
def get_preset_names() -> list[str]:
    """Get list of all preset names."""
    return list(WINDOW_PRESETS.keys())


# Update current size
def set_current_size(preset_name: str) -> None:
    """Set the current window size preset."""
    global CURRENT_WINDOW_SIZE
    if preset_name in WINDOW_PRESETS:
        CURRENT_WINDOW_SIZE = preset_name


# Return current size
def get_current_size() -> Optional[str]:
    """Get the currently selected window size preset."""
    return CURRENT_WINDOW_SIZE
