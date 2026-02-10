"""浏览器底层配置 (Browser-use / Playwright 等)。"""

from __future__ import annotations

import os
from typing import Any


def get_browser_config() -> dict[str, Any]:
    """返回 Browser-use 或 Playwright 所需配置（超时、headless 等）。"""
    return {
        "headless": os.getenv("BROWSER_HEADLESS", "true").lower() == "true",
        "timeout_ms": int(os.getenv("BROWSER_TIMEOUT_MS", "30000")),
        # 可扩展: proxy, user_agent, viewport
    }
