from __future__ import annotations
import re
from pathlib import Path
from typing import List
import pandas as pd
from ..models import Field

REQ_MAP_COLS = ["IP Name", "Base Address", "SFR Sheet Name"]
REQ_SFR_COLS = ["Reg Name", "Offset", "Field Name", "Range / Bitwidth", "Access", "Description"]

def _norm(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()

def parse_bit_range(value) -> tuple[int, int]:
    s = _norm(value).replace("[", "").replace("]", "")
    if not s:
        raise ValueError("empty Range / Bitwidth")
    if ":" in s:
        a, b = s.split(":", 1)
        msb, lsb = int(a.strip(), 0), int(b.strip(), 0)
        return max(msb, lsb), min(msb, lsb)
    # Customer sheets commonly use a single bit position, not width.
    bit = int(float(s))
    return bit, bit

def parse_excel(path: str | Path) -> List[Field]:
    path = Path(path)
    xls = pd.ExcelFile(path)
    if len(xls.sheet_names) < 1:
        raise ValueError("Expected at least 1 sheet: address map")
    
    # Check first sheet for Address Map columns
    addr_df = pd.read_excel(path, sheet_name=xls.sheet_names[0])
    missing = [c for c in REQ_MAP_COLS if c not in addr_df.columns]
    
    # Fallback to second sheet if first sheet is just a 'Header' page like in old samples
    if missing and len(xls.sheet_names) > 1:
        addr_df2 = pd.read_excel(path, sheet_name=xls.sheet_names[1])
        missing2 = [c for c in REQ_MAP_COLS if c not in addr_df2.columns]
        if not missing2:
            addr_df = addr_df2
            missing = []
            
    if missing:
        raise ValueError(f"Address map sheet missing columns: {missing}")
    fields: List[Field] = []
    for _, row in addr_df.iterrows():
        ip = _norm(row["IP Name"])
        if not ip:
            continue
        base = _norm(row["Base Address"])
        sheet = _norm(row["SFR Sheet Name"])
        if sheet not in xls.sheet_names:
            raise ValueError(f"SFR sheet {sheet!r} for IP {ip!r} not found")
        df = pd.read_excel(path, sheet_name=sheet)
        missing = [c for c in REQ_SFR_COLS if c not in df.columns]
        if missing:
            raise ValueError(f"SFR sheet {sheet!r} missing columns: {missing}")
        for _, r in df.iterrows():
            reg = _norm(r["Reg Name"])
            fld = _norm(r["Field Name"])
            if not reg or not fld:
                continue
            msb, lsb = parse_bit_range(r["Range / Bitwidth"])
            fields.append(Field(
                ip=ip, base_address=base, sheet=sheet,
                reg=reg, offset=_norm(r["Offset"]), field=fld,
                msb=msb, lsb=lsb, access=_norm(r["Access"]).upper(),
                reset_value=_norm(r.get("Reset Value", "")),
                reset_mask=_norm(r.get("Reset Mask", "")),
                testable=_norm(r.get("Testable", "")),
                constraints=_norm(r.get("Constraints", "")),
                description=_norm(r.get("Description", "")),
            ))
    return fields
