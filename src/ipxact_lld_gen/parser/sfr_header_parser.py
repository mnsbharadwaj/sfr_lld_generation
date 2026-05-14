from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, Tuple
from ..models import SfrMacroSet

DEFINE_LINE_RE = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)(?:\s+(.+?))?\s*(?://.*)?$")


def parse_defines(path: str | Path) -> Dict[str, str]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    out: Dict[str, str] = {}
    for line in text.splitlines():
        m = DEFINE_LINE_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        value = (m.group(2) or "").strip()
        out[name] = value
    return out


def expected_names(ip: str, reg: str, field: str) -> Tuple[str, str, str]:
    p = f"{ip}_{reg}_{field}".upper()
    return f"{ip}_{reg}_OFFSET".upper(), f"{p}_MASK", f"{p}_SHIFT"


def correlate_field_macros(defines: Dict[str,str], ip: str, reg: str, field: str) -> SfrMacroSet:
    off, mask, shift = expected_names(ip, reg, field)
    ms = SfrMacroSet(ip=ip, reg=reg, field=field)
    if off in defines:
        ms.offset_macro = off
        ms.macros[off] = defines[off]
    if mask in defines:
        ms.mask_macro = mask
        ms.macros[mask] = defines[mask]
    if shift in defines:
        ms.shift_macro = shift
        ms.macros[shift] = defines[shift]
    return ms
