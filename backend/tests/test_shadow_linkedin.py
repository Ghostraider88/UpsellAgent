"""Tests for the provider-backed shadow LinkedIn adapter.

The provider HTTP calls are faked — no network. We verify the gating
(flag + key), the Proxycurl payload → ``RawPerson`` mapping, graceful failure,
and that the registry only surfaces the adapter when fully enabled.
"""
from __future__ import annotations

import httpx
import pytest

from app.config import settings
from app.connectors import get_active_adapters, shadow_linkedin
from app.connectors.shadow_linkedin import ShadowLinkedInAdapter

_COMPANY_PAYLOAD = {"url": "https://www.linkedin.com/company/acme"}
_EMPLOYEES_PAYLOAD = {
    "employees": [
        {
            "profile_url": "https://www.linkedin.com/in/anna-schmidt",
            "profile": {
                "full_name": "Anna Schmidt",
                "occupation": "COO at ACME",
                "experiences": [
                    {"title": "Chief Operating Officer", "company": "ACME", "ends_at": None}
                ],
                "city": "Berlin",
                "country_full_name": "Germany",
            },
        },
        {
            "profile_url": "https://www.linkedin.com/in/tobias-berger",
            "profile": {
                "first_name": "Tobias",
                "last_name": "Berger",
                "experiences": [
                    {"title": "Head of Operations", "company": "ACME", "ends_at": None}
                ],
                "city": "Munich",
                "country_full_name": "Germany",
            },
        },
    ]
}


class _FakeResp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # always OK in the happy path
        pass

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """Stand-in for ``httpx.Client`` routing by URL to canned responses."""

    def __init__(self, routes: dict, *, raise_error: bool = False) -> None:
        self._routes = routes
        self._raise = raise_error

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def get(self, url: str, params: dict | None = None) -> _FakeResp:
        if self._raise:
            raise httpx.HTTPError("boom")
        return _FakeResp(self._routes[url])


@pytest.fixture
def shadow_enabled(monkeypatch):
    monkeypatch.setattr(settings, "enable_shadow_sources", True)
    monkeypatch.setattr(settings, "shadow_provider", "proxycurl")
    monkeypatch.setattr(settings, "proxycurl_api_key", "test-key")
    monkeypatch.setattr(settings, "shadow_max_people", 25)


def _route_client(monkeypatch, *, raise_error: bool = False) -> None:
    routes = {
        shadow_linkedin._RESOLVE_COMPANY: _COMPANY_PAYLOAD,
        shadow_linkedin._LIST_EMPLOYEES: _EMPLOYEES_PAYLOAD,
    }
    monkeypatch.setattr(
        shadow_linkedin.httpx,
        "Client",
        lambda *a, **k: _FakeClient(routes, raise_error=raise_error),
    )


def test_maps_provider_payload_to_people(monkeypatch, shadow_enabled):
    _route_client(monkeypatch)
    people = ShadowLinkedInAdapter().find_people("ACME", {"roles": ["operations"]})

    assert [p.full_name for p in people] == ["Anna Schmidt", "Tobias Berger"]

    anna, tobias = people
    assert anna.title == "Chief Operating Officer"
    assert anna.seniority == "C-Level"
    assert anna.location == "Berlin, Germany"
    assert anna.handles == {"linkedin": "https://www.linkedin.com/in/anna-schmidt"}

    # Name assembled from first/last; department inferred from the title.
    assert tobias.seniority == "Head"
    assert tobias.department == "Operations"


def test_inert_when_flag_off(monkeypatch):
    monkeypatch.setattr(settings, "enable_shadow_sources", False)
    monkeypatch.setattr(settings, "proxycurl_api_key", "test-key")
    adapter = ShadowLinkedInAdapter()
    assert adapter.is_available() is False
    assert adapter.find_people("ACME", {}) == []


def test_inert_when_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "enable_shadow_sources", True)
    monkeypatch.setattr(settings, "shadow_provider", "proxycurl")
    monkeypatch.setattr(settings, "proxycurl_api_key", None)
    assert ShadowLinkedInAdapter().is_available() is False


def test_http_error_returns_empty(monkeypatch, shadow_enabled):
    _route_client(monkeypatch, raise_error=True)
    assert ShadowLinkedInAdapter().find_people("ACME", {}) == []


def test_registry_surfaces_shadow_only_when_fully_enabled(monkeypatch, shadow_enabled):
    active = get_active_adapters(allow_shadow=True, actor="test")
    names = {a.name for a in active}
    assert "shadow_linkedin" in names
    assert "mock" in names  # compliant adapters stay active alongside

    # Without the per-request opt-in the shadow adapter stays off.
    names_no_optin = {a.name for a in get_active_adapters(allow_shadow=False)}
    assert "shadow_linkedin" not in names_no_optin
