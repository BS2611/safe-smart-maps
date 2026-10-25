"""Wording rules, same as web/lib/wording.ts: never promise safety, plain calm words."""
import re

_ALLOWED = [re.compile(r"safe smart maps?", re.I)]
_BANNED = [
    re.compile(r"\bsafest\b", re.I),
    re.compile(r"\bsafe\b", re.I),
    re.compile(r"\bsafely\b", re.I),
    re.compile(r"\bhazard(ous)?\b", re.I),
    re.compile(r"\bdangerous\b", re.I),
    re.compile(r"\bcrime[- ]free\b", re.I),
    re.compile(r"\bguarantee[sd]?\b(?! safety)", re.I),
]


def find_banned_wording(text: str) -> list[str]:
    """Banned phrases found in `text`. The product name and "do not guarantee safety" are allowed."""
    cleaned = text
    for pattern in _ALLOWED:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = re.sub(r"do(es)? not guarantee safety", " ", cleaned, flags=re.I)
    found = []
    for pattern in _BANNED:
        m = pattern.search(cleaned)
        if m:
            found.append(m.group(0))
    return found
