# Canonical Metrics Specification

This document defines the deterministic metric policy emitted by AllasCode CodeAnalyzer. The policy is versioned separately from Zig so historical reports remain comparable.

## Cyclomatic complexity

Base complexity is `1` per function. Add `1` for each occurrence of `if`, `while`, `for`, `catch` and `orelse`. For `switch`, add one for each non-`else` prong (`=>`). The `else` prong does not add complexity.

This is the AllasCode canonical policy. It is intentionally explicit because different tools disagree on how `switch`, short-circuit expressions and language-specific constructs should be counted.

Current version does not increment complexity for boolean `and`/`or`; that will be revisited when AST-based analysis lands.

## Cognitive complexity

Each decision contributes `1 + current decision nesting`. Switch prongs add one each. This metric is an approximation until the AST/CFG analyzer replaces lexical nesting.

## Comment and documentation metadata

`comment_density = comment_lines / physical_LOC` is reported only as descriptive metadata, never as a quality score or CI gate.

The analyzer also records documentation-comment counts, public API documentation coverage and TODO/FIXME/HACK/XXX markers as evidence. It does **not** require comments or public documentation comments for code quality.

Normative explanation belongs in reproducible SKILL/semantic-contract artifacts. See `SEMANTIC_CODE_STANDARD.md`.

## Semantic-operation counters

The analyzer reports evidence counters rather than claiming semantic proof:

- `error_paths`: `try`, `catch`, `return error.*`
- `optional_operations`: `.?`, `orelse`
- `pointer_operations`: dereference/address expressions and pointer/alignment casts
- `allocation_indicators`: allocator-oriented allocation calls
- `comptime_operations`: `comptime` and reflection-oriented builtins
- `cast_operations`: Zig cast builtins
- `primitive_type_exposures`: storage-specific primitive representations exposed by a public function signature
- `low_level_intrinsics`: low-level representation/conversion intrinsics used in a function body

These lexical counters will later be validated/enriched by Zig AST/ZIR.

## Semantic portability findings

### `portability.primitive_boundary` — high

A public function leaks implementation-specific primitive representations such as fixed-width numeric types, `usize`, C primitive types or raw pointer forms.

Expected remediation: expose a semantic domain type and keep the primitive representation inside its implementation.

### `portability.low_level_public` — medium

A public function directly performs low-level operations such as pointer casts, bit casts, truncation or pointer/integer conversions.

Expected remediation: encapsulate the mechanism behind a semantic function/type whose name describes the intent rather than the implementation technique.

## Default findings

- cyclomatic complexity > 10: high
- cognitive complexity > 15: high
- decision nesting > 4: medium
- function LOC > 80: medium
- primitive representation leaked through a public boundary: high
- low-level intrinsic used directly in a public function: medium

Comments are never required to silence a finding.

## Planned structural metrics

AST/ZLS/ZIR stages will add symbol references, CFG paths, fan-in, fan-out, afferent/efferent coupling, instability, dependency depth, recursion, call graph, blast radius and repair-scope score.

Semantic-analysis stages will additionally add:

- semantic type coverage;
- primitive leakage across Agent/Action/Entity/Intent contracts;
- low-level implementation adapter detection;
- semantic naming conformance;
- SKILL/contract existence and invariant coverage;
- cross-language reproducibility evidence.