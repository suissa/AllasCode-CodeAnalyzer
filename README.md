# AllasCode CodeAnalyzer

Static code analysis focused on Zig 0.16, designed to feed AllasCode CodeManager/CodeHealer with deterministic code metrics, semantic portability findings and reproducible evidence.

The first version is intentionally compiler-independent: it parses Zig source heuristically and emits stable JSON. Later layers can enrich the same schema with Zig AST/ZIR, ZLS, CFG and compiler diagnostics.

## Design goal

The analyzer does not optimize code for human source reading alone. Its primary goal is to verify that code expresses domain semantics in a form an Agent can understand and reproduce in another language.

Core rules:

- comments are descriptive evidence, not a quality requirement;
- normative explanations belong in SKILL/semantic-contract artifacts;
- public boundaries should expose semantic domain types rather than primitive storage representations;
- low-level implementation details should be encapsulated behind semantic functions/types;
- identifiers should describe intent rather than mechanism;
- portability means another implementation language can satisfy the same semantic contract without copying Zig-specific primitives.

See `docs/SEMANTIC_CODE_STANDARD.md`.

## Metrics

Per function and per file the analyzer reports:

- physical LOC and source LOC (SLOC)
- comment lines and documentation-comment lines (descriptive only)
- cyclomatic complexity (canonical AllasCode policy)
- cognitive complexity
- maximum decision nesting depth
- branch/return counts
- error paths (`try`, `catch`, `return error.*`)
- optional operations (`.?`, `orelse`)
- pointer operations and pointer casts
- allocation indicators
- comptime/reflection operations
- cast operations
- primitive type exposure at public boundaries
- low-level intrinsic usage
- TODO/FIXME/HACK/XXX markers
- public API documentation coverage (descriptive only)

Findings are generated for high complexity, high nesting, long functions, primitive representation leakage and low-level implementation details escaping semantic boundaries.

## Usage

```bash
python -m code_analyzer path/to/project
python -m code_analyzer path/to/project --format json --pretty
python -m code_analyzer src/foo.zig --fail-on high
```

The output is deterministic JSON suitable for datasets, CI gates and CodeManager evidence.

## Development

```bash
python -m unittest discover -s tests -v
```

No runtime dependency outside Python 3.12+ is required.

## Zig 0.16 roadmap

The stable schema is designed for progressive enrichment:

1. lexical/static metrics and semantic portability heuristics (implemented)
2. Zig 0.16 AST enrichment
3. ZLS symbols/types/references
4. ZIR/CFG enrichment (including zwanzig integration where useful)
5. compiler-grounded diagnostics and semantic contracts
6. dependency graph, fan-in/fan-out, coupling and blast-radius metrics
7. SKILL/contract discovery and invariant coverage
8. cross-language semantic reproducibility checks

See `docs/METRICS.md` for the canonical metric definitions.