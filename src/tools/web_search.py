# -*- coding: utf-8 -*-
"""Веб-поиск через DuckDuckGo"""

import asyncio
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, query, max_results=5):
        pass


class DuckDuckGoProvider(BaseSearchProvider):
    async def search(self, query, max_results=5):
        try:
            from duckduckgo_search import DDGS
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self._sync(query, max_results))
        except Exception as e:
            print(f"DuckDuckGo error: {e}")
            return []
    
    def _sync(self, query, max_results):
        from duckduckgo_search import DDGS
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", r.get("link", "")),
                        snippet=r.get("body", r.get("snippet", "")),
                        source="duckduckgo"
                    ))
        except Exception as e:
            print(f"DuckDuckGo sync error: {e}")
        return results


class WebSearchTool:
    """Поиск через DuckDuckGo"""
    
    def __init__(self):
        self.duckduckgo = DuckDuckGoProvider()
    
    async def search(self, query, max_results=5, context=""):
        full_query = f"{query} {context}".strip() if context else query
        return await self.duckduckgo.search(full_query, max_results)
    
    async def verify_fact(self, claim, context="programming"):
        query = f"fact check: {claim}"
        results = await self.search(query, max_results=3, context=context)
        return {"found": len(results) > 0, "results": results, "query_used": query}


def create_web_search_tool():
    return WebSearchTool()
