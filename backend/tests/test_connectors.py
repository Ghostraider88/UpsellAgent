from app.connectors import get_active_adapters
from app.connectors.mock import MockAdapter


def test_mock_adapter_returns_people():
    people = MockAdapter().find_people("ACME", {})
    assert len(people) >= 5
    assert any(p.title and "COO" in p.title.upper() or "Chief Operating" in (p.title or "") for p in people)


def test_shadow_disabled_by_default():
    # Even when the caller asks for shadow, it stays off without the global flag.
    adapters = get_active_adapters(allow_shadow=True, actor="test")
    assert all(a.mode == "compliant" for a in adapters)


def test_compliant_adapters_present():
    adapters = get_active_adapters(allow_shadow=False)
    names = {a.name for a in adapters}
    assert "mock" in names
