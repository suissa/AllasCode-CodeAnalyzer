# AllasCode CodeAnalyzer

Static code analysis focused on Zig 0.16, designed to feed AllasCode CodeManager/CodeHealer with deterministic code metrics and findings.

The first version is intentionally compiler-independent: it parses Zig source heuristically and emits stable JSON. Later layers can enrich the same schema with Zig AST/ZIR, ZLS, CFG and compiler diagnostics.

## Metrics

Per function and per file the analyzer reports:

- physical LOC and source LOC (SLOC)
- comment lines and documentation-comment lines
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
- TODO/FIXME/HACK/XXX markers
- public API documentation coverage

Findings are generated for high complexity, high nesting, long functions, undocumented public APIs and complex functions without explanatory comments.

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

1. lexical/static metrics (implemented)
2. Zig 0.16 AST enrichment
3. ZLS symbols/types/references
4. ZIR/CFG enrichment (including zwanzig integration where useful)
5. compiler-grounded diagnostics and semantic contracts
6. dependency graph, fan-in/fan-out, coupling and blast-radius metrics

See `docs/METRICS.md` for the canonical metric definitions.
