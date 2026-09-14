# Canonical Metrics Specification

This document defines the deterministic metric policy emitted by AllasCode CodeAnalyzer. The policy is versioned separately from Zig so historical reports remain comparable.

## Cyclomatic complexity

Base complexity is `1` per function. Add `1` for each occurrence of `if`, `while`, `for`, `catch` and `orelse`. For `switch`, add one for each non-`else` prong (`=>`). The `else` prong does not add complexity.

This is the AllasCode canonical policy. It is intentionally explicit because different tools disagree on how `switch`, short-circuit expressions and language-specific constructs should be counted.

Current version does not increment complexity for boolean `and`/`or`; that will be revisited when AST-based analysis lands.

## Cognitive complexity

Each decision contributes `1 + current decision nesting`. Switch prongs add one each. This metric is an approximation until the AST/CFG analyzer replaces lexical nesting.

## Documentation metrics

`comment_density = comment_lines / physical_LOC` is reported only as descriptive metadata, never as a quality score.

Primary documentation indicators are:

- public API documentation coverage
- undocumented public functions
- complex functions without explanatory comments
- TODO/FIXME/HACK/XXX markers

A public function is considered documented when it has a contiguous preceding `///` or `//!` documentation block, or a documentation line inside its detected span.

## Semantic-operation counters

The analyzer reports evidence counters rather than claiming semantic proof:

- `error_paths`: `try`, `catch`, `return error.*`
- `optional_operations`: `.?`, `orelse`
- `pointer_operations`: dereference/address expressions and pointer/alignment casts
- `allocation_indicators`: allocator-oriented allocation calls
- `comptime_operations`: `comptime` and reflection-oriented builtins
- `cast_operations`: Zig cast builtins

These lexical counters will later be validated/enriched by Zig AST/ZIR.

## Default findings

- cyclomatic complexity > 10: high
- cognitive complexity > 15: high
- decision nesting > 4: medium
- function LOC > 80: medium
- undocumented public function: medium
- cyclomatic > 7 or cognitive > 10 with no comments: medium

## Planned structural metrics

AST/ZLS/ZIR stages will add symbol references, CFG paths, fan-in, fan-out, afferent/efferent coupling, instability, dependency depth, recursion, call graph, blast radius and repair-scope score.
