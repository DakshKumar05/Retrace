"""Scam-message analyser.

Returns a 0-100 message risk score together with the exact phrases that produced
it, so the UI never has to show an unexplained number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.nlp.patterns import MITIGATING_PATTERNS, PATTERN_GROUPS

_COMPILED = [
    {
        "code": g["code"],
        "label": g["label"],
        "weight": g["weight"],
        "regexes": [re.compile(p, re.IGNORECASE) for p in g["patterns"]],  # type: ignore[arg-type]
    }
    for g in PATTERN_GROUPS
]

_COMPILED_MITIGATORS = [(code, re.compile(p, re.IGNORECASE), w) for code, p, w in MITIGATING_PATTERNS]

# UPI handles and bare phone numbers offered inside a message are a strong tell.
_UPI_RE = re.compile(r"\b[\w.\-]{3,}@(?:ok\w+|upi|ybl|paytm|axl|ibl|apl|sbi|hdfcbank|icici)\b", re.I)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)")


@dataclass
class MessageAnalysis:
    score: int
    level: str
    recommendation: str
    signals: list[dict] = field(default_factory=list)
    matched_phrases: list[str] = field(default_factory=list)
    extracted_handles: list[str] = field(default_factory=list)
    word_count: int = 0

    def as_dict(self) -> dict:
        return {
            "message_risk_score": self.score,
            "risk_level": self.level,
            "recommendation": self.recommendation,
            "signals": self.signals,
            "matched_phrases": self.matched_phrases,
            "extracted_handles": self.extracted_handles,
            "word_count": self.word_count,
        }


def _level(score: int) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    if score <= 80:
        return "HIGH"
    return "CRITICAL"


def analyze_message(text: str) -> MessageAnalysis:
    body = (text or "").strip()
    if not body:
        return MessageAnalysis(score=0, level="LOW", recommendation="NO_TEXT_SUPPLIED")

    raw = 0
    signals: list[dict] = []
    phrases: list[str] = []

    for group in _COMPILED:
        hits: list[str] = []
        for rx in group["regexes"]:  # type: ignore[index]
            for m in rx.finditer(body):
                snippet = m.group(0).strip()
                if snippet.lower() not in {h.lower() for h in hits}:
                    hits.append(snippet)
        if not hits:
            continue
        # Saturating: a second hit in the same group adds half weight, no more.
        weight = int(group["weight"]) + (int(group["weight"]) // 2 if len(hits) > 1 else 0)
        raw += weight
        phrases.extend(hits)
        signals.append(
            {
                "code": group["code"],
                "label": group["label"],
                "weight": weight,
                "category": "NLP",
                "detail": "Matched: " + ", ".join(f'"{h}"' for h in hits[:4]),
            }
        )

    handles = sorted({*_UPI_RE.findall(body)})
    phones = sorted({*_PHONE_RE.findall(body)})
    if handles or phones:
        raw += 12
        found = handles + phones
        signals.append(
            {
                "code": "PAYMENT_HANDLE_IN_MESSAGE",
                "label": "A payment destination was supplied inside the message",
                "weight": 12,
                "category": "NLP",
                "detail": "Found: " + ", ".join(found[:3]),
            }
        )

    for code, rx, weight in _COMPILED_MITIGATORS:
        match = rx.search(body)
        if match:
            raw -= weight
            # Quote the phrase, like every other signal does. Without it two
            # mitigators render as the same line twice with nothing to tell
            # them apart.
            signals.append(
                {
                    "code": code,
                    "label": "Language consistent with a legitimate settlement",
                    "weight": -weight,
                    "category": "NLP",
                    "detail": f'Matched: "{match.group(0).strip()}" — reduces risk.',
                }
            )

    score = _normalise(raw)
    level = _level(score)
    recommendation = "DO_NOT_TRANSFER_MANUALLY" if score >= 61 else (
        "VERIFY_BEFORE_ACTING" if score >= 31 else "NO_ACTION_NEEDED"
    )
    return MessageAnalysis(
        score=score,
        level=level,
        recommendation=recommendation,
        signals=sorted(signals, key=lambda s: -s["weight"]),
        matched_phrases=phrases[:12],
        extracted_handles=handles + phones,
        word_count=len(body.split()),
    )


def _normalise(raw: int) -> int:
    """Compress the tail so stacked signals cannot run away past 100."""
    raw = max(raw, 0)
    if raw <= 60:
        return min(raw, 100)
    return min(int(round(60 + (raw - 60) * 0.62)), 100)


def urgency_present(text: str | None) -> bool:
    if not text:
        return False
    result = analyze_message(text)
    return any(s["code"] in {"URGENCY", "PRESSURE"} for s in result.signals)
