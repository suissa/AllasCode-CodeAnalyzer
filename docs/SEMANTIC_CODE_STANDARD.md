# Semantic Reproducible Code Standard

## Purpose

AllasCode code SHOULD be understandable from domain semantics without requiring the reader to know the implementation language.

The target reader is primarily an Agent, not a human scanning source line by line. Explanations that are required to reproduce an artifact belong in structured, retrievable SKILL/contract artifacts rather than prose comments embedded in source code.

This standard is language-independent. Zig 0.16 is the first implementation target.

## Core principles

### 1. Semantics before representation

Public boundaries MUST expose semantic domain types instead of primitive representation types.

Avoid:

```zig
pub fn debit(account_id: u64, amount: i64) bool
```

Prefer:

```zig
pub fn debit(account_id: AccountId, amount: Money) DebitResult
```

`u64`, `i64`, byte order, pointer width, allocator layout, SIMD width and similar details are implementation choices. They are not the domain contract.

A different target language may implement `AccountId`, `Money` or `DebitResult` using completely different primitives while preserving the same semantic contract.

### 2. Low-level decisions are encapsulated behind semantic functions

Architecture-level code MUST NOT expose compiler intrinsics, pointer representation tricks, storage widths or ABI details as business meaning.

Avoid:

```zig
pub fn userKey(id: u64) u128 {
    return @as(u128, id) << 64;
}
```

Prefer a semantic boundary:

```zig
pub fn createUserKey(id: UserId) UserKey {
    return UserKey.fromUser(id);
}
```

The low-level implementation may still exist inside `UserKey.fromUser`, but callers depend on the semantic operation, not the representation technique.

### 3. Comments are evidence, not specification

Comment density is NOT a quality metric.

Comments MAY explain local facts, temporary constraints or interoperability details, but correctness MUST NOT depend on a human reading comments.

Normative construction knowledge belongs in a reproducible artifact such as a SKILL or semantic contract containing, at minimum:

- artifact/concept identity;
- purpose;
- accepted inputs and semantic types;
- outputs;
- invariants;
- forbidden states/operations;
- construction procedure;
- tests/proof obligations;
- valid example;
- invalid example;
- portability notes where implementations differ by language.

### 4. Names carry intent

Identifiers SHOULD describe domain behavior rather than mechanism.

Avoid names such as:

```text
castIdToU64
ptrToInt
copy32Bytes
makeHash128
```

Prefer semantic names such as:

```text
encodeUserId
addressIdentity
copyPayloadDigest
createEntityFingerprint
```

The implementation language is free to choose how each semantic operation is realized.

### 5. Reproducibility over commentary

A codebase is considered well explained when an Agent can reconstruct a correct implementation in another language from semantic contracts, SKILL artifacts and tests without translating source syntax mechanically.

This leads to the following portability criterion:

> If replacing the implementation language requires understanding undocumented primitive choices in source code, the abstraction boundary is incomplete.

## Analyzer rules

The first lexical implementation provides two enforceable portability findings.

### `portability.primitive_boundary`

A public function exposes a storage-specific primitive type such as `u32`, `u64`, `i32`, `f64`, `usize`, raw pointer forms, or C representation primitives.

The expected repair is to introduce a semantic type at the public boundary and keep the primitive inside its implementation.

### `portability.low_level_public`

A public function directly contains low-level intrinsics such as pointer casts, bit casts, integer-width casts, truncation, pointer/integer conversion or alignment casts.

The expected repair is to move the mechanism behind a semantic function/type and let the public function describe intent.

These rules are deliberately conservative in v0.2. AST/ZIR enrichment will later distinguish safe representation adapters from true semantic-boundary leaks.

## Non-goals

This standard does NOT prohibit primitive types internally. Machine-level implementation eventually requires concrete representation.

It prohibits allowing those choices to become the semantic API.

It also does NOT prohibit comments. It rejects comments as a substitute for machine-readable, reproducible semantic specification.

## Long-term CodeAnalyzer checks

Future versions should verify:

- semantic type coverage at public boundaries;
- raw primitive leakage across Agent/Action/Entity/Intent contracts;
- low-level intrinsics outside explicitly declared implementation adapters;
- direct storage/ABI/network representation leakage;
- semantic naming quality using the project vocabulary;
- existence and validity of the corresponding SKILL/contract artifact;
- agreement between SKILL invariants and tests;
- cross-language reproducibility tests;
- whether two implementations in different languages satisfy the same semantic contract.

The objective is not merely clean Zig. The objective is implementation-independent code semantics.