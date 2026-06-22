"""Compliant news/web adapter via SerpAPI (Google News).

Only active when ``SERPAPI_API_KEY`` is set. Used purely for *signals*
(unstructured text) that feed relationship extraction — it does not enumerate
employees.
"""
from __future__ import annotations

import json
import logging
import re

import httpx

from app.config import settings
from app.connectors.base import RawPerson, Signal

logger = logging.getLogger(__name__)


def _extract_names_azure_openai(text: str) -> list[str]:
    """Extract person names using Azure OpenAI gpt-4-nano.

    Falls back to regex if the API is unavailable or key is missing.
    """
    if not settings.azure_openai_api_key:
        logger.debug("Azure OpenAI key not set; using regex fallback for name extraction")
        return _extract_names_regex(text)

    try:
        headers = {
            "api-key": settings.azure_openai_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract ONLY real person names (first + last name) from text. "
                        "Return a JSON array like [\"John Smith\", \"Jane Doe\"]. "
                        "Return [] if no names found."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Extract person names from this text:\n{text}",
                },
            ],
            "temperature": 0,
            "max_tokens": 200,
        }

        url = (
            f"{settings.azure_openai_endpoint}openai/deployments/"
            f"{settings.azure_openai_deployment}/chat/completions"
            f"?api-version={settings.azure_openai_api_version}"
        )

        resp = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        # Extract the response text
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "[]")

        # Parse JSON array from response
        try:
            names = json.loads(content)
            if isinstance(names, list):
                return [n.strip() for n in names if isinstance(n, str) and n.strip()]
        except json.JSONDecodeError:
            logger.warning("Failed to parse OpenAI response as JSON: %s", content)

        return []
    except Exception as exc:
        logger.warning("Azure OpenAI name extraction failed: %s; falling back to regex", exc)
        return _extract_names_regex(text)


def _extract_names_regex(text: str) -> list[str]:
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
                # Extract person names using Azure OpenAI (falls back to regex).
                mentioned_names = _extract_names_azure_openai(text)

                signals.append(
                    Signal(
                        text=text,
                        url=item.get("link"),
                        mentioned_names=mentioned_names,
                        raw=item,
                    )
                )
        return signals
