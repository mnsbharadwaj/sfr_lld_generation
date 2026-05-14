from __future__ import annotations
from typing import Dict, List, Tuple
from ..models import Field, ApiDecl, SfrMacroSet
from ..semantics.rule_engine import extract_semantics
from .llm_client import LlmClient


def cname(*parts: str) -> str:
    return "_".join(p.lower() for p in parts if p)


def _indent(lines: List[str]) -> str:
    return "\n".join("    " + line if line else "" for line in lines)


def _setter_body(macros: SfrMacroSet) -> str:
    return _indent([
        f"uint32_t reg = LLD_REG32(base, {macros.offset_macro});",
        f"reg &= (uint32_t)~({macros.mask_macro});",
        f"reg |= (uint32_t)((value << {macros.shift_macro}) & {macros.mask_macro});",
        f"LLD_REG32(base, {macros.offset_macro}) = reg;",
    ])


def _getter_body(macros: SfrMacroSet) -> str:
    return _indent([
        f"return (uint32_t)((LLD_REG32(base, {macros.offset_macro}) & {macros.mask_macro}) >> {macros.shift_macro});",
    ])


def _clear_body(macros: SfrMacroSet) -> str:
    # W1C clear operation: write mask directly to the register.
    return _indent([
        f"LLD_REG32(base, {macros.offset_macro}) = {macros.mask_macro};",
    ])


def primitive_decls(field: Field, macros: SfrMacroSet) -> List[ApiDecl]:
    decls: List[ApiDecl] = []
    access = field.access.upper().strip()
    can_read = "R" in access or access in {"RO", "RW", "RC"}
    can_write = "W" in access or access in {"WO", "RW", "W1C", "W1S"}
    base = cname(field.ip, field.reg, field.field)
    if can_write and access not in {"RO"}:
        decls.append(ApiDecl(
            name=f"{base}_set",
            return_type="void",
            args="uint32_t base, uint32_t value",
            field_key=field.key,
            kind="setter",
            body=_setter_body(macros),
        ))
    if can_read and access not in {"WO"}:
        decls.append(ApiDecl(
            name=f"{base}_get",
            return_type="uint32_t",
            args="uint32_t base",
            field_key=field.key,
            kind="getter",
            body=_getter_body(macros),
        ))
    return decls


def _field_by_upper(fields: List[Field], ip: str, name: str) -> Field | None:
    name = name.upper()
    for f in fields:
        if f.ip == ip and f.field.upper() == name:
            return f
    return None


def semantic_decls(field: Field, sem: Dict, fields: List[Field], macro_map: Dict[str, SfrMacroSet]) -> List[ApiDecl]:
    decls: List[ApiDecl] = []
    tags = set(sem.get("tags", []))
    if not field.description.strip():
        return decls
    ip = field.ip.lower()
    reg = field.reg.lower()
    fld = field.field.lower()
    macros = macro_map.get(field.key)
    if not macros:
        return decls

    if "w1c" in tags:
        decls.append(ApiDecl(
            name=cname(ip, reg, "clear", fld),
            return_type="void",
            args="uint32_t base",
            field_key=field.key,
            kind="clear",
            reason="description indicates W1C/clear",
            body=_clear_body(macros),
        ))

    if "trigger" in tags:
        helper_name = cname(ip, fld if fld not in {"start", "trigger"} else "start")
        lines = [f"{cname(field.ip, field.reg, field.field)}_set(base, 1U);"]
        related = sem.get("related_fields", []) or []
        done_field = None
        err_field = None
        for r in related:
            rf = _field_by_upper(fields, field.ip, r)
            if not rf:
                continue
            if r.upper() in {"DONE", "READY", "COMPLETE", "COMPLETED"}:
                done_field = rf
            if r.upper() in {"ERR", "ERROR", "FAULT"}:
                err_field = rf
        if done_field is None and "poll" in tags:
            for rf in fields:
                if rf.ip == field.ip and rf.field.upper() in {"DONE", "READY", "COMPLETE", "COMPLETED"}:
                    done_field = rf
                    break
        if done_field:
            lines.extend([
                f"while ({cname(done_field.ip, done_field.reg, done_field.field)}_get(base) == 0U) {{",
                "    /* wait */",
                "}",
            ])
        if err_field:
            lines.extend([
                f"if ({cname(err_field.ip, err_field.reg, err_field.field)}_get(base) != 0U) {{",
                "    return -1;",
                "}",
            ])
        lines.append("return 0;")
        decls.append(ApiDecl(
            name=helper_name,
            return_type="int",
            args="uint32_t base",
            field_key=field.key,
            kind="helper",
            reason="description indicates trigger/start",
            body=_indent(lines),
        ))

    if "reset" in tags:
        lines = [
            f"{cname(field.ip, field.reg, field.field)}_set(base, 1U);",
            "return 0;",
        ]
        decls.append(ApiDecl(
            name=cname(ip, reg, "reset"),
            return_type="int",
            args="uint32_t base",
            field_key=field.key,
            kind="helper",
            reason="description indicates reset",
            body=_indent(lines),
        ))
    return decls


def generate_expected_decls(fields: List[Field], macro_map: Dict[str, SfrMacroSet], llm_config_path: str | None = None) -> tuple[List[ApiDecl], List[Dict]]:
    decls: List[ApiDecl] = []
    sem_report: List[Dict] = []
    
    llm_client = None
    if llm_config_path:
        try:
            llm_client = LlmClient(llm_config_path)
        except Exception as e:
            print(f"Failed to init LLM client: {e}")

    for f in fields:
        macros = macro_map.get(f.key)
        if not macros or not macros.mask_macro or not macros.shift_macro or not macros.offset_macro:
            sem_report.append({"field": f.key, "warning": "No matching OFFSET/MASK/SHIFT macros in sfr.h; API not generated"})
            continue
        sem = extract_semantics(f, fields)
        before = len(decls)
        decls.extend(primitive_decls(f, macros))
        
        llm_success = False
        if llm_client and f.description.strip():
            llm_body = llm_client.generate_lld_function(f.description, f.key, f.reg, f.field, f.access)
            if llm_body:
                ip = f.ip.lower()
                fld = f.field.lower()
                name = cname(ip, fld if fld not in {"start", "trigger"} else "start")
                decls.append(ApiDecl(
                    name=name,
                    return_type="void",
                    args="uint32_t base",
                    field_key=f.key,
                    kind="llm_helper",
                    reason="description processed by LLM",
                    raw_code=llm_body,
                ))
                llm_success = True
                
        if not llm_success:
            decls.extend(semantic_decls(f, sem, fields, macro_map))
            
        sem_report.append({"field": f.key, "semantics": sem, "apis": [d.name for d in decls[before:] if d.field_key == f.key]})
    # de-duplicate by API name, keeping first
    seen = set(); unique = []
    for d in decls:
        if d.name not in seen:
            unique.append(d); seen.add(d.name)
    return unique, sem_report


def render_lld_header(decls: List[ApiDecl], header_guard: str = "GENERATED_LLD_H", sfr_include: str | None = None) -> str:
    lines = [
        "/* Generated header-only LLD. No AUTOGEN markers used. */",
        f"#ifndef {header_guard}",
        f"#define {header_guard}",
        "",
        "#include <stdint.h>",
        "",
    ]
    if sfr_include:
        lines.append(f'#include "{sfr_include}"')
        lines.append("")
    lines.extend([
        "#ifndef LLD_REG32",
        "#define LLD_REG32(base, offset) (*(volatile uint32_t *)((uintptr_t)(base) + (uintptr_t)(offset)))",
        "#endif",
        "",
    ])
    last_key = None
    for d in decls:
        if d.field_key != last_key:
            lines.append("")
            lines.append(f"/* {d.field_key} */")
            last_key = d.field_key
        lines.append(d.render())
        lines.append("")
    lines.extend([f"#endif /* {header_guard} */", ""])
    return "\n".join(lines)
