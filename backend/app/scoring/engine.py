"""ICP scoring: how well a person matches the Ideal Customer Profile.

Uses Anthropic Claude for nuanced reasoning when ``ANTHROPIC_API_KEY`` is set,
and otherwise falls back to a transparent keyword/seniority heuristic so the
tool is fully functional offline.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from app.config import settings


@dataclass
class ScoreResult:
    score: int  # 0-100
    rationale: str
    matched_signals: list[str]


_SENIORITY_WEIGHT = {
    "c-level": 1.0,
    "vp": 0.85,
    "head": 0.75,
    "director": 0.75,
    "lead": 0.6,
    "manager": 0.55,
}


def _heuristic_score(person: dict, icp: dict) -> ScoreResult:
    """Transparent fallback: keyword overlap on role + seniority weighting."""
    title = (person.get("current_title") or "").lower()
    department = (person.get("department") or "").lower()
    haystack = f"{title} {department}"

    keywords = [k.lower() for k in icp.get("keywords", [])]
    roles = [r.lower() for r in icp.get("roles", [])]
    functions = [f.lower() for f in icp.get("functions", [])]
    terms = set(keywords + roles + functions)

    matched = sorted({t for t in terms if t and t in haystack})
    coverage = len(matched) / len(terms) if terms else 0.0

    seniority = (person.get("seniority") or "").lower()
    sen_weight = max(
        (w for key, w in _SENIORITY_WEIGHT.items() if key in seniority), default=0.4
    )

    target_seniority = [s.lower() for s in icp.get("seniority", [])]
    seniority_bonus = 0.0
    if target_seniority and any(s in seniority for s in target_seniority):
        seniority_bonus = 0.15

    raw = 0.6 * coverage + 0.4 * sen_weight + seniority_bonus
    score = max(0, min(100, round(raw * 100)))

    if matched:
        rationale = (
            f"Title/department match on {', '.join(matched)}; "
            f"seniority '{person.get('seniority') or 'unknown'}'."
        )
    else:
        rationale = (
            f"No direct ICP keyword match; scored on seniority "
            f"'{person.get('seniority') or 'unknown'}'."
        )
    return ScoreResult(score=score, rationale=rationale, matched_signals=matched)


def _llm_score(person: dict, icp: dict) -> ScoreResult:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        "You score how well a person matches a B2B Ideal Customer Profile (ICP) "
        "for a sales upsell. Return ONLY JSON: "
        '{"score": <0-100 int>, "rationale": "<one sentence>", '
        '"matched_signals": ["..."]}.\n\n'
        f"ICP: {json.dumps(icp)}\n"
        f"Person: {json.dumps(person)}"
    )
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    data = json.loads(text[text.find("{") : text.rfind("}") + 1])
    return ScoreResult(
        score=max(0, min(100, int(data.get("score", 0)))),
        rationale=str(data.get("rationale", "")),
        matched_signals=list(data.get("matched_signals", [])),
    )


def score_person(person: dict, icp: dict) -> ScoreResult:
    """Score one person against the ICP, preferring the LLM when available."""
    if settings.llm_enabled:
        try:
            return _llm_score(person, icp)
        except Exception:  # noqa: BLE001 — never let scoring crash the pipeline
            pass
    return _heuristic_score(person, icp)
