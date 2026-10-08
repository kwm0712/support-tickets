from __future__ import annotations

import os
import sys
from pathlib import Path


def _application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def main() -> int:
    root = _application_root()
    app = root / "streamlit_v03.py"
    if not app.exists():
        raise RuntimeError(f"COMPELEC ONE Business UI fehlt: {app}")

    if getattr(sys, "frozen", False):
        data_root = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "COMPELEC" / "ONE Business" / "data"
        os.environ.setdefault("CCS_DATA_DIR", str(data_root))
    os.chdir(root)
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")

    sys.argv = [
        "streamlit",
        "run",
        str(app),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false",
    ]

    from streamlit.web.cli import main as streamlit_main

    return int(streamlit_main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
