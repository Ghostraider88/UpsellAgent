"""Compliant news/web adapter via SerpAPI (Google News).

Only active when ``SERPAPI_API_KEY`` is set. Used purely for *signals*
(unstructured text) that feed relationship extraction — it does not enumerate
employees.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.connectors.base import RawPerson, Signal

logger = logging.getLogger(__name__)


class SerpApiNewsAdapter:
    name = "serpapi_news"
    mode = "compliant"

    def is_available(self) -> bool:
        return bool(settings.serpapi_api_key)

    def find_people(self, company_name: str, icp: dict) -> list[RawPerson]:
        # This source provides signals, not a roster.
        return []

    def find_signals(self, company_name: str) -> list[Signal]:
        if not self.is_available():
            return []
        try:
            resp = httpx.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_news",
                    "q": company_name,
                    "api_key": settings.serpapi_api_key,
                },
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("SerpAPI failed for %r: %s", company_name, exc)
            return []

        news_results = data.get("news_results", [])
        logger.info(
            "SerpAPI for %r: got %d news results (status=%s error=%s)",
            company_name,
            len(news_results),
            data.get("search_metadata", {}).get("status"),
            data.get("error"),
        )
        signals: list[Signal] = []
        for item in news_results[:25]:
            text = " ".join(
                filter(None, [item.get("title"), item.get("snippet")])
            )
            if text:
                signals.append(Signal(text=text, url=item.get("link"), raw=item))
        return signals
