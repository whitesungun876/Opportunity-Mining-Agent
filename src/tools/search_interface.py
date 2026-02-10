"""抽象搜索接口：支持多源切换 (SERP / 自建 API / Browser-use)。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SearchInterface(ABC):
    """统一搜索接口，便于切换 SerpAPI、Bing、Browser-use 等。"""

    @abstractmethod
    def search(self, query: str, limit: int = 20, **kwargs: Any) -> list[dict[str, Any]]:
        """执行搜索，返回条目列表。每条约目建议含 content/snippet/url 等。"""
        pass


class PlaceholderSearch(SearchInterface):
    """占位实现：返回空列表，用于本地跑通图。"""

    def search(self, query: str, limit: int = 20, **kwargs: Any) -> list[dict[str, Any]]:
        return []


def get_search_client(source: str = "placeholder") -> SearchInterface:
    """根据配置返回对应搜索实现。"""
    if source == "placeholder":
        return PlaceholderSearch()
    # 可扩展: "serpapi", "bing", "browser_use"
    return PlaceholderSearch()
