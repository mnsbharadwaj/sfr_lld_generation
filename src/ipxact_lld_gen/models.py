from __future__ import annotations
from dataclasses import dataclass, field as dc_field
from typing import List, Dict, Optional, Tuple

@dataclass(frozen=True)
class Field:
    ip: str
    base_address: str
    sheet: str
    reg: str
    offset: str
    field: str
    msb: int
    lsb: int
    access: str
    reset_value: str = ""
    reset_mask: str = ""
    testable: str = ""
    constraints: str = ""
    description: str = ""

    @property
    def key(self) -> str:
        return f"{self.ip}.{self.reg}.{self.field}"

    @property
    def width(self) -> int:
        return self.msb - self.lsb + 1

@dataclass
class SfrMacroSet:
    ip: str
    reg: str
    field: Optional[str] = None
    offset_macro: Optional[str] = None
    mask_macro: Optional[str] = None
    shift_macro: Optional[str] = None
    macros: Dict[str, str] = dc_field(default_factory=dict)

@dataclass(frozen=True)
class ApiDecl:
    name: str
    return_type: str
    args: str
    field_key: str
    kind: str
    reason: str = ""
    body: Optional[str] = None
    raw_code: Optional[str] = None

    def render(self) -> str:
        if self.raw_code:
            return self.raw_code.rstrip()
        if self.body:
            return f"static inline {self.return_type} {self.name}({self.args})\n{{\n{self.body.rstrip()}\n}}"
        return f"{self.return_type} {self.name}({self.args});"

@dataclass
class FunctionDeclNode:
    name: str
    return_type: str
    args: str
    start: int
    end: int
    text: str

    def signature(self) -> str:
        return f"{self.return_type.strip()} {self.name}({self.args.strip()})"
