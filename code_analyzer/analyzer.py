from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterable


FUNCTION_RE = re.compile(r"(?P<prefix>\bpub\s+)?\bfn\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
DECISION_RE = re.compile(r"\b(if|while|for|catch|orelse)\b")
MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
CAST_RE = re.compile(r"@(intCast|floatCast|ptrCast|alignCast|bitCast|enumFromInt|intFromEnum|truncate|as)\b")
COMPTIME_RE = re.compile(r"\bcomptime\b|@(TypeOf|typeInfo|This|field|hasDecl)\b")
OPTIONAL_RE = re.compile(r"\.\?|\borelse\b")
POINTER_RE = re.compile(r"\.\*|@ptrCast\b|@alignCast\b|&\s*[A-Za-z_(]")
ALLOCATION_RE = re.compile(r"\.(alloc|allocSentinel|create|dupe|realloc)\s*\(|\ballocator\b")
ERROR_RE = re.compile(r"\btry\b|\bcatch\b|return\s+error\.")
RETURN_RE = re.compile(r"\breturn\b")
SWITCH_RE = re.compile(r"\bswitch\s*\(")
SWITCH_PRONG_RE = re.compile(r"=>")
ELSE_PRONG_RE = re.compile(r"\belse\s*=>")

# Primitive representation details should not escape semantic boundaries. `bool`,
# `void`, `noreturn`, `type` and error mechanics are intentionally omitted: they
# describe control/semantic shape rather than a storage width chosen by Zig.
PRIMITIVE_TYPE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"u(?:8|16|32|64|128|256|size)|"
    r"i(?:8|16|32|64|128|256|size)|"
    r"f(?:16|32|64|80|128)|"
    r"c_(?:char|short|ushort|int|uint|long|ulong|longlong|ulonglong)|"
    r"comptime_(?:int|float)"
    r")(?![A-Za-z0-9_])"
)
LOW_LEVEL_INTRINSIC_RE = re.compile(
    r"@(ptrCast|alignCast|bitCast|intCast|floatCast|truncate|constCast|volatileCast|"
    r"addrSpaceCast|intFromPtr|ptrFromInt)\b"
)
RAW_POINTER_TYPE_RE = re.compile(r"(?<![A-Za-z0-9_])(?:\*|\[\*c?\]|\[\*:.*?\])")


@dataclass(frozen=True)
class FunctionMetrics:
    name: str
    public: bool
    line_start: int
    line_end: int
    loc: int
    sloc: int
    comment_lines: int
    doc_comment_lines: int
    documented: bool
    cyclomatic_complexity: int
    cognitive_complexity: int
    max_nesting_depth: int
    branch_count: int
    return_count: int
    error_paths: int
    optional_operations: int
    pointer_operations: int
    allocation_indicators: int
    comptime_operations: int
    cast_operations: int
    primitive_type_exposures: int
    low_level_intrinsics: int
    markers: dict[str, int]


@dataclass(frozen=True)
class Finding:
    severity: str
    rule: str
    message: str
    line: int | None = None
    function: str | None = None


def _mask_strings(line: str) -> str:
    out: list[str] = []
    i = 0
    quote: str | None = None
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\" and i + 1 < len(line):
                out.extend("  ")
                i += 2
                continue
            if ch == quote:
                quote = None
            out.append(" ")
            i += 1
            continue
        if ch in {'"', "'"}:
            quote = ch
            out.append(" ")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _split_code_and_comments(source: str) -> tuple[list[str], list[str | None], list[bool]]:
    code_lines: list[str] = []
    comments: list[str | None] = []
    docs: list[bool] = []
    for raw in source.splitlines():
        masked = _mask_strings(raw)
        idx = masked.find("//")
        if idx >= 0:
            comment = raw[idx + 2 :].strip()
            is_doc = masked[idx:].startswith("///") or masked[idx:].startswith("//!")
            code_lines.append(raw[:idx])
            comments.append(comment)
            docs.append(is_doc)
        else:
            code_lines.append(raw)
            comments.append(None)
            docs.append(False)
    return code_lines, comments, docs


def _brace_delta(code: str) -> int:
    masked = _mask_strings(code)
    return masked.count("{") - masked.count("}")


def _find_functions(code_lines: list[str]) -> list[tuple[str, bool, int, int]]:
    functions: list[tuple[str, bool, int, int]] = []
    i = 0
    while i < len(code_lines):
        line = code_lines[i]
        m = FUNCTION_RE.search(line)
        if not m:
            i += 1
            continue

        start = i
        depth = 0
        seen_body = False
        j = i
        while j < len(code_lines):
            current = code_lines[j]
            if "{" in _mask_strings(current):
                seen_body = True
            depth += _brace_delta(current)
            if seen_body and depth <= 0:
                break
            j += 1

        functions.append((m.group("name"), bool(m.group("prefix")), start, min(j, len(code_lines) - 1)))
        i = max(i + 1, j + 1)
    return functions


def _function_signature(code_lines: list[str], start: int) -> str:
    parts: list[str] = []
    depth = 0
    seen_open = False
    for line in code_lines[start:]:
        masked = _mask_strings(line)
        parts.append(masked.strip())
        depth += masked.count("(") - masked.count(")")
        seen_open = seen_open or "(" in masked
        if seen_open and depth <= 0:
            break
    return " ".join(parts)


def _decision_metrics(lines: list[str]) -> tuple[int, int, int, int]:
    cyclomatic = 1
    cognitive = 0
    branch_count = 0
    max_nesting = 0
    decision_stack: list[int] = []
    brace_depth = 0

    for raw in lines:
        code = _mask_strings(raw)
        leading_closes = len(code) - len(code.lstrip("}"))
        if leading_closes:
            brace_depth = max(0, brace_depth - leading_closes)
            decision_stack = [d for d in decision_stack if d <= brace_depth]

        decisions = list(DECISION_RE.finditer(code))
        switch_count = len(SWITCH_RE.findall(code))
        prongs = len(SWITCH_PRONG_RE.findall(code)) - len(ELSE_PRONG_RE.findall(code))

        for _ in decisions:
            cyclomatic += 1
            branch_count += 1
            nesting = len(decision_stack)
            cognitive += 1 + nesting
            max_nesting = max(max_nesting, nesting + 1)
            if "{" in code:
                decision_stack.append(brace_depth + 1)

        if switch_count:
            branch_count += switch_count
            cognitive += switch_count * (1 + len(decision_stack))
            max_nesting = max(max_nesting, len(decision_stack) + 1)
        if prongs > 0:
            cyclomatic += prongs
            branch_count += prongs
            cognitive += prongs

        brace_depth += code.count("{") - code.count("}") + leading_closes
        brace_depth = max(0, brace_depth)
        decision_stack = [d for d in decision_stack if d <= brace_depth]

    return cyclomatic, cognitive, max_nesting, branch_count


def _count_markers(comments: Iterable[str | None]) -> dict[str, int]:
    counts = {"TODO": 0, "FIXME": 0, "HACK": 0, "XXX": 0}
    for comment in comments:
        if not comment:
            continue
        for match in MARKER_RE.finditer(comment):
            key = match.group(1).upper()
            counts[key] += 1
    return counts


def _has_preceding_doc(start: int, comments: list[str | None], docs: list[bool], code_lines: list[str]) -> bool:
    i = start - 1
    found = False
    while i >= 0:
        if docs[i]:
            found = True
            i -= 1
            continue
        if comments[i] is not None and not code_lines[i].strip():
            i -= 1
            continue
        if not code_lines[i].strip() and comments[i] is None:
            break
        break
    return found


def analyze_source(source: str, *, path: str = "<memory>") -> dict:
    code_lines, comments, docs = _split_code_and_comments(source)
    functions_raw = _find_functions(code_lines)
    functions: list[FunctionMetrics] = []
    findings: list[Finding] = []

    for name, public, start, end in functions_raw:
        f_code = code_lines[start : end + 1]
        f_comments = comments[start : end + 1]
        f_docs = docs[start : end + 1]
        cyclomatic, cognitive, nesting, branches = _decision_metrics(f_code)
        documented = _has_preceding_doc(start, comments, docs, code_lines) or any(f_docs)
        sloc = sum(1 for line in f_code if line.strip())
        comment_lines = sum(1 for c in f_comments if c is not None)
        doc_lines = sum(1 for d in f_docs if d)
        text = "\n".join(f_code)
        signature = _function_signature(code_lines, start)
        primitive_exposures = len(PRIMITIVE_TYPE_RE.findall(signature)) if public else 0
        raw_pointer_exposures = len(RAW_POINTER_TYPE_RE.findall(signature)) if public else 0
        low_level_intrinsics = len(LOW_LEVEL_INTRINSIC_RE.findall(text))

        metrics = FunctionMetrics(
            name=name,
            public=public,
            line_start=start + 1,
            line_end=end + 1,
            loc=end - start + 1,
            sloc=sloc,
            comment_lines=comment_lines,
            doc_comment_lines=doc_lines,
            documented=documented,
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            max_nesting_depth=nesting,
            branch_count=branches,
            return_count=len(RETURN_RE.findall(text)),
            error_paths=len(ERROR_RE.findall(text)),
            optional_operations=len(OPTIONAL_RE.findall(text)),
            pointer_operations=len(POINTER_RE.findall(text)),
            allocation_indicators=len(ALLOCATION_RE.findall(text)),
            comptime_operations=len(COMPTIME_RE.findall(text)),
            cast_operations=len(CAST_RE.findall(text)),
            primitive_type_exposures=primitive_exposures + raw_pointer_exposures,
            low_level_intrinsics=low_level_intrinsics,
            markers=_count_markers(f_comments),
        )
        functions.append(metrics)

        if cyclomatic > 10:
            findings.append(Finding("high", "complexity.cyclomatic", f"Function {name} has cyclomatic complexity {cyclomatic} (> 10).", start + 1, name))
        if cognitive > 15:
            findings.append(Finding("high", "complexity.cognitive", f"Function {name} has cognitive complexity {cognitive} (> 15).", start + 1, name))
        if nesting > 4:
            findings.append(Finding("medium", "complexity.nesting", f"Function {name} reaches decision nesting depth {nesting} (> 4).", start + 1, name))
        if metrics.loc > 80:
            findings.append(Finding("medium", "size.long_function", f"Function {name} spans {metrics.loc} lines (> 80).", start + 1, name))

        # Comments are evidence, not a quality requirement. Reproducible semantic
        # intent belongs in SKILL/contract artifacts and in semantic identifiers.
        if metrics.primitive_type_exposures:
            findings.append(Finding(
                "high",
                "portability.primitive_boundary",
                f"Public function {name} exposes {metrics.primitive_type_exposures} low-level primitive representation(s); use semantic domain types at the boundary.",
                start + 1,
                name,
            ))
        if public and low_level_intrinsics:
            findings.append(Finding(
                "medium",
                "portability.low_level_public",
                f"Public function {name} contains {low_level_intrinsics} low-level intrinsic operation(s); encapsulate them behind a semantic function.",
                start + 1,
                name,
            ))

    total_lines = len(source.splitlines())
    source_lines = sum(1 for line in code_lines if line.strip())
    comment_lines = sum(1 for c in comments if c is not None)
    doc_comment_lines = sum(1 for d in docs if d)
    public_functions = [f for f in functions if f.public]
    documented_public = [f for f in public_functions if f.documented]
    marker_counts = _count_markers(comments)
    primitive_exposures = sum(f.primitive_type_exposures for f in functions)
    low_level_public = sum(f.low_level_intrinsics for f in public_functions)

    for marker, count in marker_counts.items():
        if count:
            findings.append(Finding("info", f"comment.{marker.lower()}", f"Found {count} {marker} marker(s)."))

    return {
        "schema_version": "0.2.0",
        "language": "zig",
        "language_target": "0.16",
        "path": path,
        "summary": {
            "loc": total_lines,
            "sloc": source_lines,
            "comment_lines": comment_lines,
            "doc_comment_lines": doc_comment_lines,
            "comment_density": (comment_lines / total_lines) if total_lines else 0.0,
            "functions": len(functions),
            "public_functions": len(public_functions),
            "documented_public_functions": len(documented_public),
            "public_api_documentation_coverage": (len(documented_public) / len(public_functions)) if public_functions else 1.0,
            "primitive_boundary_exposures": primitive_exposures,
            "low_level_public_intrinsics": low_level_public,
            "markers": marker_counts,
        },
        "functions": [asdict(f) for f in functions],
        "findings": [asdict(f) for f in findings],
    }


def analyze_file(path: str | Path) -> dict:
    p = Path(path)
    return analyze_source(p.read_text(encoding="utf-8"), path=str(p))


def analyze_path(path: str | Path) -> dict:
    root = Path(path)
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*.zig") if ".zig-cache" not in p.parts and "zig-out" not in p.parts)
    analyses = [analyze_file(p) for p in files]
    findings = [f | {"path": item["path"]} for item in analyses for f in item["findings"]]
    function_count = sum(item["summary"]["functions"] for item in analyses)
    public_count = sum(item["summary"]["public_functions"] for item in analyses)
    documented_public = sum(item["summary"]["documented_public_functions"] for item in analyses)
    primitive_exposures = sum(item["summary"]["primitive_boundary_exposures"] for item in analyses)
    low_level_public = sum(item["summary"]["low_level_public_intrinsics"] for item in analyses)
    return {
        "schema_version": "0.2.0",
        "language": "zig",
        "language_target": "0.16",
        "root": str(root),
        "summary": {
            "files": len(analyses),
            "functions": function_count,
            "public_functions": public_count,
            "documented_public_functions": documented_public,
            "public_api_documentation_coverage": (documented_public / public_count) if public_count else 1.0,
            "primitive_boundary_exposures": primitive_exposures,
            "low_level_public_intrinsics": low_level_public,
            "findings": len(findings),
        },
        "files": analyses,
        "findings": findings,
    }
