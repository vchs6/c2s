# Semantic Fact Product Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline and maintain this existing OpenSpec task set as the only authoritative product backlog.

**Goal:** Deliver a usable, request-driven semantic facts Skill that can traverse the fixed real Rust `regex` and Python `click` projects, return complete facts for the requested scope, and expose every unhandled or unavailable fact as a gap.

**Architecture:** Build the M1 vertical slice first: Python package, typed fact/evidence/coverage records, exhaustive path inventory, language-aware parsers, exact query projection, and JSON/Markdown output. Expand from declarations into definitions and supported behavior facts while preserving provenance and explicit unsupported/unobserved gaps. Validate against every eligible source file and parser fact in the pinned projects, with exhaustive coverage manifests and query-level verification.

**Approaches:** (1) Reuse third-party code graphs as the product model; rejected because prior evidence shows graph indexing silently omits project files and cannot represent semantic completeness. (2) Write one-off regex/Python text scanners; rejected because they cannot reliably preserve syntax, identities, or byte positions. (3) Use full inventory + Python AST + Rust Tree-sitter, native Cargo metadata where required, and a language-neutral fact contract; selected because it matches existing experiments, scales to exhaustive syntax traversal, and can report limits honestly.

**Tech Stack:** Python 3.12, Python `ast`/`tomllib`, Tree-sitter Rust grammar, Cargo metadata where available, JSON Schema 2020-12/jsonschema, unittest; fixed OpenSpec tasks and regex/click commits from the repository.

**Spec:** `openspec/specs/semantic-fact-model/spec.md`, `semantic-fact-query/spec.md`, `semantic-analysis-scope/spec.md`, `lazy-semantic-fact-construction/spec.md`, `semantic-analysis-quality/spec.md`; implementation details and task IDs in the existing `openspec/changes/*/tasks.md`.

## Global Constraints

- Preserve E0–E4 as distinct semantic scales and one identity per subject.
- Return the complete top-level fact set requested, without recursive expansion; report every gap and reason.
- The selected project tree is the analysis range; do not silently skip tests, examples, nested or ignored files.
- Never claim semantic facts from syntax alone; distinguish declarations, static structure, behavior evidence and unknowns.
- Do not mutate the source project; keep caches/artifacts under ignored `.local/`.
- Report private/independent acceptance as unrun where unavailable; this does not block development.

## Review Focus

- Ignored/test/example/nested files and symlink/out-of-range paths must appear in inventory or explicit gap records.
- Rust macro, cfg, generated, dynamic Python, and unresolved cross-file bindings must not be promoted to verified facts.
- Overloaded/same-named declarations must retain stable path/scope identity and UTF-8 byte spans.
- Unknown selectors may not silently narrow scope; malformed requests fail before acquisition.
- JSON and Markdown must derive from the same result and show identical fact IDs and gaps.

## File Map

- `skill/src/c2s_skill/`: model, inventory, Rust/Python acquisition, query, presentation, CLI.
- `skill/contracts/`: JSON schemas and predicate catalog.
- `skill/tests/`: unit and integration coverage, including pinned real-project exhaustive tests.
- `skill/README.md`: install, supported fact classes, limits, and end-to-end use.
- `docs/development/reviews/semantic-facts/`: reproducible exhaustive run manifests and coverage summaries.
- Existing OpenSpec tasks: update only the task slices whose acceptance evidence is genuinely complete.

## Tasks

### Task 1: Freeze the executable M1 contract

- [ ] Derive records and CLI shape from the listed specs and existing M1 designs; record exact selector behavior and claim/coverage statuses.
- [ ] Add schema/model tests first, prove they fail, implement typed records and validation.
- [ ] Run contract tests and strict OpenSpec validation.

### Task 2: Exhaustive project inventory and source preservation

- [ ] Add tests for ignored/test/nested files, symlinks, unreadable paths, and UTF-8 byte offsets.
- [ ] Implement deterministic inventory with explicit inclusion/gap records and source hashes.
- [ ] Prove source trees are unchanged before/after an inventory pass.

### Task 3: Rust and Python fact acquisition

- [ ] Add failing real-source cases for declarations, imports, members, functions, signatures, bodies, and source evidence.
- [ ] Implement Python AST and Rust Tree-sitter traversal; use native metadata only for supported project/workspace claims.
- [ ] Traverse every eligible source file and record parse status and all emitted fact IDs per file.

### Task 4: Request-driven query and exhaustive projection

- [ ] Add tests for each supported selector, unknown selectors, malformed requests, and full-result versus bounded presentation.
- [ ] Implement query normalization, on-demand acquisition, cached fact reuse, exact top-level projection, and explicit gaps.
- [ ] Generate JSON and Markdown from one immutable result and compare IDs/statuses.

### Task 5: Persistence, continuation, and evidence accounting

- [ ] Test repeated query, supplement, interrupted acquisition, stale source, and write failure.
- [ ] Implement versioned local store, deterministic identity, supersedes validation, and run profile.
- [ ] Ensure saved results are bound to source commit/hash, parser version and platform.

### Task 6: Full real-project traversal and verification

- [ ] Run all product tests and full exhaustive traversal on pinned regex and click.
- [ ] Verify per-file coverage, no unexplained omissions, query completeness for every supported fact category, and source immutability.
- [ ] Record exact commands, counts, unsupported cases and failures; update only proven OpenSpec task checkboxes and user docs.

## Execution Notes

This is a multi-session sized implementation. Work continuously through the ordered tasks, keeping each source/test/real-project result reviewable. Do not declare the whole product complete until Task 6 meets every listed check; report partial progress and concrete blockers when session or tool limits interrupt execution.

## Progress — 2026-11-05, continued

- Task 1: partial. Added JSON Schema 2020-12 contract validation for fact IDs, shared subject IDs, E0–E4 layers, claim modes, coverage, gaps and inventory; fact IDs are project-root namespaced, and Python/Rust function declaration, documentation and algorithm facts share one subject ID. Selectors reject malformed empty targets before scan. A full typed/versioned domain model, typed cross-layer references, lineage and complete M1 validation remain outstanding.
- Task 2: partial, materially expanded. Project scan now includes a deterministic full visible-tree inventory (excluding VCS `.git` control dirs), records unhandled/unsupported paths in JSON and Markdown, follows no symlinks, and includes every regular file in source digest invalidation. Tests cover ignored/hidden/nested content, symlinks, unsupported paths and digest changes. Permission-based unreadable-path integration and stronger snapshot consistency remain outstanding.
- Task 3: partial, materially expanded. Python AST and Rust Tree-sitter parse every `.py`/`.rs` file in both pinned projects; function declarations are E2, Python decorator calls are excluded from function-body algorithm steps, and supported Python assignment/loop/with/exception targets plus Rust tuple, struct, tuple-struct, slice, or, reference and captured `let` patterns are queryable E4 `local_binding` facts. Cargo `metadata --no-deps --offline` adds all seven regex workspace members as E1 metadata facts. Type/call binding, Rust range and constant pattern interpretation, build/cfg/macro expansion, Python packaging metadata and remaining E0–E4 categories remain outstanding.
- Ruling: nested callable bodies retain their own `subject_id`; querying an outer function returns its direct body steps and does not attribute a nested function's steps to the outer function. This avoids claiming inner code executes as part of outer code; the cost if wrong is that users must separately request nested function bodies, and the outer function's lexical contents are not fully expanded into E4 facts.
- Task 4: partial. Added pre-acquisition validation for malformed selectors, explicit gaps for missing target subjects/project metadata, ensured all-supported queries include Cargo workspace facts when available, and suppresses type/function bodies from list queries until explicitly requested. Existing category projections work; broad natural-language query planning and fact-level lazy acquisition remain outstanding.
- Task 5: partial. SQLite result cache now invalidates on any visible project-tree change, including non-source documentation, and keys by analyzer/parser/Python/platform/Cargo profile digest. Cache paths inside the analyzed project are rejected before reads/writes; cache write failure preserves facts and reports persistence separately from semantic completeness. Per-fact transactions, durable interrupted-acquisition continuation and supersedes lineage remain outstanding.
- Task 6: partial. The 2026-11-06 exhaustive manifest records every parsed source file and every emitted fact ID and is reproducible with `scripts/generate_semantic_fact_inventory.py`. regex returns 54,315 supported facts (including seven workspace members); click returns 23,779 after excluding decorator calls and including Python loop, with and exception targets from function-body steps and adding supported local binding facts. Every unique function selector target was also batch-queried and its returned subject facts compared with the complete scan: 3,395 regex and 1,797 click targets, all matched; both projects have unique result IDs and zero parse failures, with 224/155 unhandled paths listed. Click's upstream suite passed 2262 with 24 skipped, 31000 deselected, 1 xfailed. Cargo metadata works offline, but regex `cargo test --workspace --all-targets` cannot start compilation because `proxy:8080` is unreachable and the offline cache lacks `aho-corasick`. E0–E4 semantics and private acceptance are not complete.

Final verification: product tests 45/45; repository maintenance tests 35/35; strict OpenSpec validation 21/21; artifact verification passed; `git diff --check` passed; click upstream suite 2262 passed, 24 skipped, 31000 deselected, 1 xfailed; regenerated regex/click inventory records 54,315/23,779 unique facts, 227/227 plus 91/91 source parses, and all 3,395/1,797 distinct function selector targets return the exact facts for their selected subjects. regex Cargo metadata resolves seven workspace packages offline; `cargo test --workspace --all-targets` remains blocked before compilation by the unreachable HTTP proxy and missing offline dependency cache. E0–E4 semantics and private acceptance are not complete. Detailed evidence is in `docs/development/reviews/semantic-facts/2026-11-06-exhaustive-inventory.json`.

## Progress — 2026-11-06, structured algorithm model

- OpenSpec `define-layered-semantic-fact-model` task 4.1: partial. Added a versioned JSON Schema for algorithm purpose, source-located steps, regions, typed control/data edges, and omissions; added structural/reference validation that rejects duplicate identities, dangling regions/edges, missing compute order/type rules, and opaque regions without explicit source, impact, unknowns and effect boundaries. Seven tests pass. This validator checks contract shape only: it does not yet include the operation/input/output contract model, create AlgorithmDescription facts from Python/Rust syntax, verify source coverage, project pseudocode, or validate behavior semantics.
- Current environment contains the locally installed Rust toolchain at `.local/cargo/bin`; `cargo test --workspace --all-targets --offline` is now verified to fail before compilation because `aho-corasick` is absent from the offline cache. Online retry still cannot connect through `proxy:8080` to `index.crates.io`. The historical inventory verification row records the prior environment state and must be refreshed when acquisition changes are next tested.
