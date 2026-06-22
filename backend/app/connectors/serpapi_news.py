"""Compliant news/web adapter via SerpAPI (Google News).

Only active when ``SERPAPI_API_KEY`` is set. Used purely for *signals*
(unstructured text) that feed relationship extraction — it does not enumerate
employees.
"""
from __future__ import annotations

import logging
import re

import httpx

from app.config import settings
from app.connectors.base import RawPerson, Signal

logger = logging.getLogger(__name__)


def _extract_names_from_text(text: str) -> list[str]:
    """Extract likely person names from news text using simple heuristics.

    Matches sequences of 2+ capitalized words (first + last name), which keeps
    real people like "David Wystrach" while filtering single-word noise such as
    company names ("Dachser") and generic title words.
    """
    if not text or len(text) < 10:
        return []

    # Require at least two capitalized words in a row → a first + last name.
    pattern = r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)+)\b"
    candidates = re.findall(pattern, text)

    # Drop multi-word phrases that are clearly not people (org/role phrases).
    stop = {
        "Air", "Sea", "Food", "Logistics", "Supply", "Chain", "Fuel", "Cells",
        "Truck", "Trucks", "Mercedes", "Benz", "Daimler", "Container", "News",
        "Press", "Release", "Market", "Insight", "Transport", "Intelligence",
        "Northern", "Ireland", "South", "East", "Asia", "New", "York",
        "Takes", "Delivery", "Next", "Generation", "Hydrogen", "Electric",
        "Building", "Opens", "Expands", "Grows", "Service", "Services",
        "Group", "Company", "Network", "Global", "Europe", "Germany", "Spain",
    }
    names = []
    for c in candidates:
        words = c.split()
        # Keep only if no word is an obvious org/place token.
        if not any(w in stop for w in words):
            names.append(c)

    # Deduplicate, cap to limit noise.
    return list(dict.fromkeys(names))[:10]


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
                # Extract person names using heuristics from title + snippet.
                mentioned_names = _extract_names_from_text(text)

                signals.append(
                    Signal(
                        text=text,
                        url=item.get("link"),
                        mentioned_names=mentioned_names,
                        raw=item,
                    )
                )
        return signals
