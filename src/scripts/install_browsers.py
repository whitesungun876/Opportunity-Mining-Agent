"""Install Playwright Chromium browser (required for Collector / browser-use)."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    """Run: playwright install chromium."""
    r = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=False,
    )
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
