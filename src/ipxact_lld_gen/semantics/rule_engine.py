from __future__ import annotations
import re
from typing import Dict, List
from ..models import Field

RULES = [
    ("w1c", re.compile(r"write\s*1\s*(to)?\s*clear|w1c", re.I)),
    ("trigger", re.compile(r"start|trigger|initiate|kick", re.I)),
    ("self_clear", re.compile(r"self[- ]?clear|auto[- ]?clear|cleared\s+by\s+hardware|hardware\s+clears", re.I)),
    ("poll", re.compile(r"poll|wait\s+.*done|before\s+issuing\s+next", re.I)),
    ("reset", re.compile(r"reset|soft\s+reset", re.I)),
    ("enable", re.compile(r"enable", re.I)),
    ("status", re.compile(r"status|done|busy|ready|error|interrupt", re.I)),
]

def extract_semantics(field: Field, all_fields: List[Field]) -> Dict:
    desc = field.description or ""
    tags = [name for name, pat in RULES if pat.search(desc)]
    related = []
    names = {f.field.upper(): f for f in all_fields if f.ip == field.ip}
    for token in re.findall(r"\b[A-Z][A-Z0-9_]{1,}\b", desc):
        if token in names and token != field.field.upper():
            related.append(token)
    confidence = 0.45 + min(0.45, len(tags) * 0.12)
    if not desc.strip():
        confidence = 1.0
    return {"tags": tags, "related_fields": sorted(set(related)), "confidence": round(confidence, 2), "description_present": bool(desc.strip())}
