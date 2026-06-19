"""Place-name matching utilities.

The #1 headache when joining a researcher's data table to administrative
boundaries is name mismatch: "Comilla" vs "Cumilla", "Chittagong" vs
"Chattogram", trailing words like "District" / "Division" / "Zila", and
diacritics. This module normalizes names, applies a small alias table of
well-known renamings, and falls back to fuzzy matching.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple

try:
    from rapidfuzz import fuzz, process

    _HAVE_RAPIDFUZZ = True
except Exception:  # pragma: no cover
    _HAVE_RAPIDFUZZ = False

# Known historical / spelling renames -> canonical (normalized) form.
ALIASES: Dict[str, str] = {
    "chittagong": "chattogram",
    "comilla": "cumilla",
    "dacca": "dhaka",
    "jessore": "jashore",
    "bogra": "bogura",
    "barisal": "barishal",
    "rangpur city": "rangpur",
    "noakhali": "noakhali",
    "bombay": "mumbai",
    "calcutta": "kolkata",
    "madras": "chennai",
    "bangalore": "bengaluru",
    "pondicherry": "puducherry",
    "saigon": "ho chi minh",
    "rangoon": "yangon",
}

# Words to strip from administrative names before comparison.
_SUFFIX_WORDS = {
    "district", "division", "zila", "zilla", "upazila", "thana",
    "subdistrict", "sub-district", "city", "corporation", "metropolitan",
    "county", "province", "governorate", "state", "region", "prefecture",
    "department", "municipality", "tehsil", "taluk", "taluka", "union",
    "pourashava", "sadar", "district.",
}


def normalize(name: str) -> str:
    """Lowercase, strip diacritics, punctuation, and admin suffix words."""
    if name is None:
        return ""
    # strip diacritics
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    # normalize separators / punctuation to spaces
    s = re.sub(r"[\-_/.,'`]", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # drop trailing/leading admin suffix words
    tokens = [t for t in s.split(" ") if t and t not in _SUFFIX_WORDS]
    s = " ".join(tokens) if tokens else s
    # apply alias table
    return ALIASES.get(s, s)


def match_one(
    name: str,
    candidates: List[str],
    threshold: float = 80.0,
) -> Tuple[Optional[str], float]:
    """Match ``name`` to the best candidate.

    Returns ``(matched_candidate, score)`` where score is 0-100. Returns
    ``(None, score)`` when the best score is below ``threshold``.
    """
    if not candidates:
        return None, 0.0
    norm_name = normalize(name)
    norm_map = {normalize(c): c for c in candidates}

    # exact normalized hit
    if norm_name in norm_map:
        return norm_map[norm_name], 100.0

    if not _HAVE_RAPIDFUZZ:
        return None, 0.0

    choice, score, _ = process.extractOne(
        norm_name, list(norm_map.keys()), scorer=fuzz.WRatio
    )
    if score >= threshold:
        return norm_map[choice], float(score)
    return None, float(score)


def match_table(
    names: List[str],
    candidates: List[str],
    threshold: float = 80.0,
) -> Dict[str, Optional[str]]:
    """Map every name in ``names`` to a candidate (or ``None``)."""
    return {n: match_one(n, candidates, threshold)[0] for n in names}


def report(
    names: List[str],
    candidates: List[str],
    threshold: float = 80.0,
):
    """Return (matched_dict, unmatched_list) for quick diagnostics."""
    matched = {}
    unmatched = []
    for n in names:
        m, _score = match_one(n, candidates, threshold)
        if m is None:
            unmatched.append(n)
        else:
            matched[n] = m
    return matched, unmatched
