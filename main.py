import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import KaresabariApp
from window_config import get_preset_names, DEFAULT_WINDOW_SIZE


# Run the app entry flow and process command-line options
def main() -> None:
    window_preset = None

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg in ("--help", "-h"):
            print(main.__doc__)
            print("\nAvailable presets:")
            for preset in get_preset_names():
                print(f"  - {preset}")
            return

        elif arg in ("--list-sizes", "-l"):
            from window_config import get_all_presets
            print("Available window size presets:\n")
            for key, size in get_all_presets().items():
                print(f"  {key:20} : {size.width:4}x{size.height:4}  ({size.description})")
            return

        elif arg == "--reset-db":
            from database import reset_db
            reset_db(keep_catalogue=True)
            print("Database reset complete (catalogue kept).")
            return

        elif arg == "--reset-db-empty":
            from database import reset_db
            reset_db(keep_catalogue=False)
            print("Database reset complete (catalogue cleared).")
            return

        elif arg == "--size" and len(sys.argv) > 2:
            window_preset = sys.argv[2]
            if window_preset not in get_preset_names():
                print(f"Error: Unknown preset '{window_preset}'")
                print(f"Use 'python main.py --list-sizes' to see available presets")
                return
            print(f"Launching with preset: {window_preset}")

        else:
            print(f"Unknown argument: {arg}")
            print("Use 'python main.py --help' for usage information")
            return

    app = KaresabariApp(window_preset=window_preset)
    app.mainloop()


if __name__ == "__main__":
    main()
