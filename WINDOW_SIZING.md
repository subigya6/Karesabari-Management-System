# Karesabari Window Sizing for Testing

## Overview

Karesabari now supports responsive window sizing for testing the UI on different devices and screen sizes. You can:

1. Launch the app with a specific window size preset
2. Switch window sizes at runtime using the Dev Panel
3. Use environment variables for automatic sizing

## Quick Start

### Launch with Default Phone Size
```bash
# iPhone 12 size (390x844)
python main.py --size iPhone_12

# iPhone 14 Pro Max size (428x926)
python main.py --size iPhone_Pro

# iPad Air size (820x1180)
python main.py --size iPad_Air
```

### Launch with Tablet Size
```bash
# iPad Mini (768x1024)
python main.py --size iPad_Mini

# iPad Pro 11-inch (834x1194)
python main.py --size iPad_Pro_11
```

### Launch with Default Desktop
```bash
# Default 1080p desktop (1150x750)
python main.py

# Or explicitly:
python main.py --size Desktop_1080p
```

## Available Presets

### iPhone & Android Phones
- `iPhone_SE` - 375x812 (iPhone SE 2020)
- `iPhone_8` - 375x667 (iPhone 8 / SE Gen 1)
- `iPhone_12` - 390x844 (iPhone 12 / 13)
- `iPhone_14` - 390x844 (iPhone 14 / 15)
- `iPhone_Pro` - 428x926 (iPhone 14/15 Pro Max)
- `Pixel_5` - 393x851 (Google Pixel 5)
- `Pixel_6` - 412x915 (Google Pixel 6)
- `Samsung_S21` - 360x800 (Samsung Galaxy S21)
- `Samsung_S22` - 360x800 (Samsung Galaxy S22)

### Tablets
- `iPad_Mini` - 768x1024
- `iPad_Air` - 820x1180
- `iPad_Pro_11` - 834x1194

### Desktop
- `Desktop_1080p` - 1150x750 (Default)
- `Desktop_1440p` - 1440x900
- `Desktop_4K` - 1920x1200

## Runtime Switching

Once the app is running, go to the **Dev Panel** tab and look for the "Window Size" card. You can:

1. **Select a preset** from the dropdown menu
2. **See the dimensions** of the selected size in the info label
3. **Click "Apply Size"** to resize the window immediately

The window will resize smoothly, and the layout will adapt to the new size.

## Environment Variables

You can also set the window size using an environment variable:

```bash
set KARESABARI_WINDOW=iPhone_14
python main.py
```

Or on macOS/Linux:
```bash
export KARESABARI_WINDOW=iPad_Air
python main.py
```

## Command-Line Help

```bash
# Show help and usage
python main.py --help

# Show all available presets with dimensions
python main.py --list-sizes
```

## UI Responsive Design

The Karesabari UI is designed to be responsive:

- All spacing, fonts, and sizes are defined in `theme.py`
- Layouts use grid weight configurations for scaling
- Images scale proportionally with the window
- Text wraps appropriately for smaller screens
- Sidebar remains fixed on the left (adapts on very small screens)

## Development Workflow

1. **Test default desktop layout**: `python main.py`
2. **Test phone layouts**: `python main.py --size iPhone_14`
3. **Test tablet layouts**: `python main.py --size iPad_Pro_11`
4. **Switch dynamically**: Use Dev Panel at runtime

## Implementation Details

### Files Modified:
- `window_config.py` - New file with window size definitions
- `app.py` - Updated to accept window presets
- `main.py` - Command-line argument support
- `dev_panel.py` - Runtime window size switcher UI

### Key Classes:
- `WindowSize` (dataclass) - Defines a window size preset
- Window size presets are stored in `WINDOW_PRESETS` dictionary

## Adding Custom Presets

Edit `window_config.py` and add to the `WINDOW_PRESETS` dictionary:

```python
WINDOW_PRESETS: dict[str, WindowSize] = {
    ...
    "MyCustomSize": WindowSize("My Size", 800, 600, "Custom 4:3 ratio"),
    ...
}
```

Then you can use it:
```bash
python main.py --size MyCustomSize
```

## Notes

- Minimum window size is set to match the selected preset
- Window resizing respects the current UI layout constraints
- All changes are temporary and don't affect configuration files
- For persistent window size, set the `KARESABARI_WINDOW` environment variable
