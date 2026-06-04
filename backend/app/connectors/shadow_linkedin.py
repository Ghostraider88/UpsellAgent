"""Shadow / fallback adapter for LinkedIn-sourced people (provider-backed).

DISABLED by default. This adapter is the "hidden fallback" mode: it only
activates when BOTH ``ENABLE_SHADOW_SOURCES=true`` AND the caller passes the
admin flag at request time. Every activation is audit-logged (see
``connectors.registry``) and any data it produces is tagged ``source_mode=shadow``
so it is clearly distinguishable in the UI and exports.

The data is fetched through a **licensed data provider** (Proxycurl by default),
not a self-built scraper — there is deliberately no anti-bot / fingerprint /
CAPTCHA circumvention here. Even so: pulling LinkedIn/Xing profile data violates
those platforms' ToS and is GDPR-sensitive in the EU. Run this only with a
documented lawful basis. The flag gate, audit log, provenance tagging and
suppression list exist precisely to keep that use defensible.
"""
from __future__ import annotations

import logging
import re

import httpx

from app.config import settings
from app.connectors.base import RawPerson, Signal

logger = logging.getLogger("upsell.connectors.shadow")

# Proxycurl REST endpoints (https://nubela.co/proxycurl/docs).
_PROXYCURL_BASE = "https://nubela.co/proxycurl/api"
_RESOLVE_COMPANY = f"{_PROXYCURL_BASE}/linkedin/company/resolve"
_LIST_EMPLOYEES = f"{_PROXYCURL_BASE}/linkedin/company/employees/"

_TIMEOUT = 30.0

# Title → seniority. Values match the keys used by the graph builder's
# ``_SENIORITY_RANK`` (compared case-insensitively), so inferred reporting lines
# work for shadow-sourced people too.
_SENIORITY_PATTERNS: list[tuple[str, str]] = [
    (r"\b(c[eoftmi]o|chief|cxo|founder|owner|geschäftsführer|managing director)\b", "C-Level"),
    (r"\b(vp|vice president)\b", "VP"),
    (r"\bhead\b", "Head"),
    (r"\bdirector\b", "Director"),
    (r"\b(lead|principal|leiter)\b", "Lead"),
    (r"\bmanager\b", "Manager"),
]

_DEPARTMENT_PATTERNS: list[tuple[str, str]] = [
    (r"\b(engineer|software|developer|devops|data|automation|tech|cto)\b", "Engineering"),
    (r"\b(operations|ops|coo)\b", "Operations"),
    (r"\b(finance|accounting|controll|cfo)\b", "Finance"),
    (r"\b(sales|account executive|business development|revenue)\b", "Sales"),
    (r"\b(marketing|growth|brand|demand)\b", "Marketing"),
    (r"\bproduct\b", "Product"),
    (r"\b(people|human resources|\bhr\b|talent|recruit)\b", "People"),
]


def _match(patterns: list[tuple[str, str]], title: str | None) -> str | None:
    t = (title or "").lower()
    for pattern, label in patterns:
        if re.search(pattern, t):
            return label
    return None


def _current_title(profile: dict) -> str | None:
    """Best-effort current title from a Proxycurl person profile."""
    for exp in profile.get("experiences") or []:
        # An experience with no ``ends_at`` is the current role.
        if not exp.get("ends_at") and exp.get("title"):
            return exp["title"]
    return profile.get("occupation") or profile.get("headline")


def _profile_to_person(profile: dict, profile_url: str | None) -> RawPerson | None:
    full_name = profile.get("full_name") or " ".join(
        filter(None, [profile.get("first_name"), profile.get("last_name")])
    ).strip()
    if not full_name:
        return None
    title = _current_title(profile)
    location = ", ".join(
        filter(None, [profile.get("city"), profile.get("country_full_name")])
    ) or None
    handles = {"linkedin": profile_url} if profile_url else {}
    return RawPerson(
        full_name=full_name,
        title=title,
        seniority=_match(_SENIORITY_PATTERNS, title),
        department=_match(_DEPARTMENT_PATTERNS, title),
        location=location,
        handles=handles,
        raw=profile,
    )


def _role_search(icp: dict) -> str | None:
    """Build a Proxycurl ``role_search`` regex from the ICP roles/keywords.

    Prefiltering the employee roster server-side keeps provider cost down and
    returns more relevant people instead of an undifferentiated dump.
    """
    terms = [*(icp.get("roles") or []), *(icp.get("keywords") or [])]
    terms = [re.escape(t.strip()) for t in terms if t and t.strip()]
    return "|".join(terms) if terms else None


class ShadowLinkedInAdapter:
    name = "shadow_linkedin"
    mode = "shadow"

    def _provider_key(self) -> str | None:
        if settings.shadow_provider == "proxycurl":
            return settings.proxycurl_api_key
        if settings.shadow_provider == "brightdata":
            return settings.brightdata_api_key
        return None

    def is_available(self) -> bool:
        # Gated by the global feature flag AND a configured provider key. Per-
        # request admin gating is enforced in the registry / pipeline layer.
        return settings.enable_shadow_sources and bool(self._provider_key())

    def find_people(self, company_name: str, icp: dict) -> list[RawPerson]:
        if not self.is_available():
            return []
        if settings.shadow_provider != "proxycurl":
            logger.warning(
                "Shadow provider %r not implemented; only 'proxycurl' is wired up.",
                settings.shadow_provider,
            )
            return []

        headers = {"Authorization": f"Bearer {self._provider_key()}"}
        try:
            with httpx.Client(timeout=_TIMEOUT, headers=headers) as client:
                company_url = self._resolve_company(client, company_name)
                if not company_url:
                    return []
                return self._list_people(client, company_url, icp)
        except httpx.HTTPError as exc:
            logger.warning("Shadow LinkedIn fetch failed for %s: %s", company_name, exc)
            return []

    def _resolve_company(self, client: httpx.Client, company_name: str) -> str | None:
        resp = client.get(_RESOLVE_COMPANY, params={"company_name": company_name})
        resp.raise_for_status()
        return resp.json().get("url")

    def _list_people(
        self, client: httpx.Client, company_url: str, icp: dict
    ) -> list[RawPerson]:
        params = {
            "url": company_url,
            "page_size": settings.shadow_max_people,
            "employment_status": "current",
            # Return full profiles inline so we avoid a per-person follow-up call.
            "enrich_profiles": "enrich",
        }
        role_search = _role_search(icp)
        if role_search:
            params["role_search"] = role_search

        resp = client.get(_LIST_EMPLOYEES, params=params)
        resp.raise_for_status()
        data = resp.json()

        people: list[RawPerson] = []
        for emp in data.get("employees", [])[: settings.shadow_max_people]:
            profile = emp.get("profile") or {}
            person = _profile_to_person(profile, emp.get("profile_url"))
            if person:
                people.append(person)
        return people

    def find_signals(self, company_name: str) -> list[Signal]:
        # Signals (news / co-mentions) are sourced from the compliant news
        # adapter; this adapter only contributes the people roster.
        return []
