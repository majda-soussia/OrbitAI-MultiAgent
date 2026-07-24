import sys
from utils.settings import set_debug, is_debug_enabled

if __name__ == "__main__":
    if len(sys.argv) > 1:
        set_debug(sys.argv[1].lower() in ("on", "1", "true"))
    print(f"Debug actuellement: {'ON' if is_debug_enabled() else 'OFF'}")