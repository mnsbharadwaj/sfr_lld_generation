from __future__ import annotations
import re
from pathlib import Path
from typing import Dict
from ..models import FunctionDeclNode

# Safe lightweight AST-like parser for C header prototypes and static inline functions.
# No AUTOGEN markers are required. This intentionally avoids broad multi-line regexes.
_PROTOTYPE_LINE_RE = re.compile(r"^\s*(?P<ret>[A-Za-z_][\w\s\*]*?)\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^;{}]*)\)\s*;\s*$")
_FUNC_HEAD_LINE_RE = re.compile(r"^\s*(?P<ret>[A-Za-z_][\w\s\*]*?)\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^;{}]*)\)\s*\{\s*$")

TOKEN_RE = re.compile(
    r'(?P<string>"(?:\\.|[^"\\])*")|'
    r'(?P<char>\'(?:\\.|[^\'\\])*\')|'
    r'(?P<lcomment>//[^\n]*)|'
    r'(?P<bcomment>/\*[\s\S]*?\*/)|'
    r'(?P<lbrace>\{)|'
    r'(?P<rbrace>\})'
)


def _strip_line_comment(line: str) -> str:
    return line.split('//', 1)[0]


def _valid(ret: str, name: str) -> bool:
    if name in {"if", "while", "for", "switch"}:
        return False
    words = set(ret.split())
    if "typedef" in words or "define" in words:
        return False
    return True


def _find_matching_brace(text: str, start_index: int) -> int:
    """Finds the matching closing brace for the opening brace at start_index.
    Assumes text[start_index] == '{'. Returns the index immediately after '}'.
    """
    depth = 0
    for m in TOKEN_RE.finditer(text, start_index):
        if m.group('lbrace'):
            depth += 1
        elif m.group('rbrace'):
            depth -= 1
            if depth == 0:
                return m.end()
    return len(text)


def parse_lld_header(path: str | Path) -> tuple[str, Dict[str, FunctionDeclNode]]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines(keepends=True)
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line)
    # Add a final offset for EOF
    offsets.append(pos)

    nodes: Dict[str, FunctionDeclNode] = {}
    i = 0
    while i < len(lines):
        raw_line = lines[i]
        line = _strip_line_comment(raw_line).strip()
        # Skip preprocessor and comments.
        if not line or line.startswith('#') or line.startswith('/*') or line.startswith('*'):
            i += 1
            continue

        m = _FUNC_HEAD_LINE_RE.match(raw_line)
        if m and _valid(m.group('ret'), m.group('name')):
            name = m.group('name').strip()
            ret = ' '.join(m.group('ret').split())
            args = ' '.join(m.group('args').split())
            start = offsets[i]
            
            brace_idx = text.find('{', offsets[i])
            if brace_idx != -1:
                end = _find_matching_brace(text, brace_idx)
                
                # Check if there's a newline immediately following the brace to include it
                if end < len(text) and text[end] == '\n':
                    end += 1
                elif end + 1 < len(text) and text[end:end+2] == '\r\n':
                    end += 2

                nodes[name] = FunctionDeclNode(name=name, return_type=ret, args=args, start=start, end=end, text=text[start:end])
                
                # advance i past the function
                while i < len(lines) and offsets[i] < end:
                    i += 1
                continue

        m = _PROTOTYPE_LINE_RE.match(raw_line)
        if m and _valid(m.group('ret'), m.group('name')):
            name = m.group('name').strip()
            ret = ' '.join(m.group('ret').split())
            args = ' '.join(m.group('args').split())
            start = offsets[i]
            end = offsets[i] + len(raw_line)
            nodes[name] = FunctionDeclNode(name=name, return_type=ret, args=args, start=start, end=end, text=text[start:end])
        i += 1
    return text, nodes
