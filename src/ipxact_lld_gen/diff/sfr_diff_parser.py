from __future__ import annotations
import re
from pathlib import Path
from typing import Set, Dict

DEFINE_LINE = re.compile(r"^[+-]\s*#\s*define\s+([A-Za-z_]\w*)\b", re.M)

def parse_changed_macros(diff_path: str | Path | None) -> Set[str]:
    if not diff_path:
        return set()
    text = Path(diff_path).read_text(encoding="utf-8", errors="ignore")
    return set(DEFINE_LINE.findall(text))

def macro_to_field_key(macro: str) -> str | None:
    # Expected DMA_CTRL_START_MASK/SHIFT -> DMA.CTRL.START
    m = re.match(r"([A-Z0-9]+)_([A-Z0-9]+)_([A-Z0-9_]+)_(MASK|SHIFT)$", macro)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return None

def impacted_fields_from_macros(macros: Set[str]) -> Set[str]:
    out = set()
    for m in macros:
        k = macro_to_field_key(m)
        if k:
            out.add(k)
    return out
