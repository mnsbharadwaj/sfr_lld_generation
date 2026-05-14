from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional, Set
from ..models import ApiDecl
from ..parser.lld_header_ast_parser import parse_lld_header


def _insert_support_preamble(text: str, support_preamble: str | None) -> str:
    if not support_preamble:
        return text
    needed = []
    for line in support_preamble.splitlines():
        stripped = line.strip()
        if not stripped:
            needed.append(line)
            continue
        if stripped.startswith('#include'):
            if stripped not in text:
                needed.append(line)
        elif 'LLD_REG32' in stripped:
            # Add the whole LLD_REG32 block only if not already present.
            if '#define LLD_REG32' not in text:
                needed.append(line)
        elif '#ifndef LLD_REG32' in support_preamble and '#define LLD_REG32' not in text:
            needed.append(line)
        else:
            if stripped not in text:
                needed.append(line)
    block = '\n'.join(needed).strip()
    if not block:
        return text

    lines = text.splitlines(keepends=True)
    insert_after = 0
    for idx, line in enumerate(lines):
        st = line.strip()
        if st.startswith('#ifndef') or st.startswith('#define') or st.startswith('#include') or not st:
            insert_after = idx + 1
            continue
        break
    return ''.join(lines[:insert_after]) + block + '\n\n' + ''.join(lines[insert_after:])


def patch_lld_header(existing_lld: str | Path, expected: List[ApiDecl], output_path: str | Path, impacted_fields: Optional[Set[str]] = None, support_preamble: str | None = None) -> Dict:
    """Patch without markers. Uses AST-like function/prototype nodes by byte offsets.

    If impacted_fields is provided, only functions whose field_key is impacted are inserted/replaced.
    Existing unrelated declarations/functions remain unchanged.
    """
    text, nodes = parse_lld_header(existing_lld)
    replacements = []
    inserted = []
    unchanged = []
    filtered = [d for d in expected if impacted_fields is None or d.field_key in impacted_fields]
    for d in filtered:
        rendered = d.render()
        node = nodes.get(d.name)
        if node:
            if " ".join(node.text.split()) == " ".join(rendered.split()):
                unchanged.append(d.name)
            else:
                replacements.append((node.start, node.end, rendered, d.name, node.text))
        else:
            inserted.append(d)

    new_text = text
    for start, end, rendered, name, old in sorted(replacements, key=lambda x: x[0], reverse=True):
        new_text = new_text[:start] + rendered + "\n" + new_text[end:]

    if inserted:
        block = ["", "/* Added by AST LLD updater: header-only static inline functions; no AUTOGEN markers used. */"]
        for d in inserted:
            block.append(f"/* {d.field_key} : {d.kind} */")
            block.append(d.render())
            block.append("")
        insert_text = "\n".join(block)
        idx = new_text.rfind("#endif")
        if idx != -1:
            new_text = new_text[:idx] + insert_text + "\n" + new_text[idx:]
        else:
            new_text = new_text.rstrip() + "\n" + insert_text + "\n"

    new_text = _insert_support_preamble(new_text, support_preamble)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(new_text, encoding="utf-8")
    return {
        "mode": "ast_no_markers_header_only",
        "replaced": [r[3] for r in replacements],
        "inserted": [d.name for d in inserted],
        "unchanged": unchanged,
        "impacted_fields": sorted(impacted_fields) if impacted_fields else None,
        "output": str(output_path),
    }
