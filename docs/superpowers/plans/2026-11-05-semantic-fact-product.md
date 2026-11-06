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
- Task 6: partial. The 2026-11-06 exhaustive manifest records every parsed source file and every emitted fact ID and is reproducible with `scripts/generate_semantic_fact_inventory.py`. regex returns 54,315 supported facts (including seven workspace members); click returns 23,779 after excluding decorator calls and including Python loop, with and exception targets from function-body steps and adding supported local binding facts. Every unique function selector target was also batch-queried and its returned subject facts compared with the complete scan: 3,395 regex and 1,797 click targets, all matched; both projects have unique result IDs and zero parse failures, with 224/155 unhandled paths listed. Click's upstream suite passed 2262 with 24 skipped, 31000 deselected, 1 xfailed. Regex workspace tests now pass with stable `cargo test --workspace --offline` (1,405 passed, 6 ignored); `--all-targets` fails only at a nightly-only benchmark. E0–E4 semantics and private acceptance are not complete.

Final verification: product tests 45/45; repository maintenance tests 35/35; strict OpenSpec validation 21/21; artifact verification passed; `git diff --check` passed; click upstream suite 2262 passed, 24 skipped, 31000 deselected, 1 xfailed; regenerated regex/click inventory records 54,315/23,779 unique facts, 227/227 plus 91/91 source parses, and all 3,395/1,797 distinct function selector targets return the exact facts for their selected subjects. Regex Cargo metadata resolves seven workspace packages; the real workspace test suite passes 1,405 tests with 6 ignored using stable offline Cargo. `--all-targets` encounters the repository's nightly-only bench feature. E0–E4 semantics and private acceptance are not complete. Detailed evidence is in `docs/development/reviews/semantic-facts/2026-11-06-exhaustive-inventory.json`.

## Progress — 2026-11-06, structured algorithm model

- OpenSpec `define-layered-semantic-fact-model` task 4.1: partial. Added a versioned JSON Schema for algorithm purpose, source-located steps, regions, typed control/data edges, and omissions; added structural/reference validation that rejects duplicate identities, dangling regions/edges, missing compute order/type rules, and opaque regions without explicit source, impact, unknowns and effect boundaries. Twenty-one focused algorithm/CLI tests pass. The schema requires input/output, precondition, normal/error/termination outcome, effect and ordering sections, each with an evidence-backed coverage state; reference validation checks the exact category set. Added initial Python AST and Rust Tree-sitter lowering APIs with source byte spans, nested control regions and explicit contract/control/data-flow gaps; real Click and regex functions validate. A dedicated `algorithm` CLI request now exposes the Python/Rust lowering for one source function with digest, structural diagnostics and gaps; real Click/regex fixtures validate. This remains separate from `function:` fact projection, does not verify evidence identities/source coverage, and does not project pseudocode or prove behavior semantics. Regression tests ensure Rust semicolon-discarded literals are not returns and terminal loop bodies do not gain fabricated continuation edges.
- Current environment contains the locally installed Rust toolchain at `.local/cargo/bin`. Real regex `cargo test --workspace --offline` passes 1,405 tests with 6 ignored. `--all-targets` reaches compilation but fails on `regex-syntax/benches/bench.rs` because stable Rust rejects its `#![feature(test)]`; benchmarks need nightly and are excluded from the successful test command.


## Progress — 2026-11-06, project-wide algorithm traversal

- Added `algorithm --all-functions`: it walks every function declaration emitted for all Python/Rust project files, returns one source-located structured algorithm per function, and reports parse/unsupported-path gaps. File syntax trees are indexed once and reused while lowering functions. Click real project: 91/91 files parsed and 1,897/1,897 functions analyzed, 155 unhandled paths reported; regex: 227/227 files parsed and 4,342/4,342 functions analyzed, 224 unhandled paths reported. No function lowering failures occurred. The command returns status 2 because the outputs remain semantically partial; `whole_project_semantics_complete` is always false. This improves traversal breadth but does not finish type/call binding, dynamic/macro/cfg semantics, full data flow, or integration into `function:` query output.


## Progress — 2026-11-06, M1 identity contract slice

- Added versioned `contracts/semantic-model/types.json` and `fact.schema.json`, a pinned `requirements-semantic-model.txt`, the `c2s_semantic_contract` package, identity registration with evidence union and source-key/kind/domain conflict rejection, structural validation plus local subject/evidence references, and identity/byte-range diagnostics. Added public developer-side tests and contract documentation. Seven M1 tests pass and the schema checks under Draft 2020-12. This is a partial implementation slice: catalog validation and source-observation verification are not implemented; shared-workspace tests are not independent acceptance, and the task's external #7/#10 consumer criterion has not been demonstrated. The authoritative M1 checklist remains open.

## Progress — 2026-11-06, M1 closed predicate catalog slice

- Added the closed 1.0.0 M1 catalog bundle for `project.name`, `project.language_declared`, and `workspace.member`, including role types/kinds, layer, cardinality, claim modes, comparison policy, and supported constraint IDs. Added a Draft 2020-12 catalog schema, canonical artifact digests, a pinned manifest digest, and validation for catalog drift, unknown predicates/rules, malformed roles, dangling type references, mixed versions, and fact role/kind mismatches. Seventeen focused semantic-model tests pass; full `npm test` passed 52 tests, strict OpenSpec validation passed 21/21, artifact checks passed, Python compilation and `git diff --check` passed. Task 1.2.1 remains open pending end-to-end cross-module consumption evidence; no independent/private acceptance was performed.

## Progress — 2026-11-06, M1 phased validation slice

- Added regression coverage for stage dependency stopping, preservation of identity-kind conflicts with related registration references, and the rule that a structurally/reference-valid subset remains `consistency=undetermined`. Updated `rules.md` to document the four ordered stages and the distinction between checked validity and semantic consistency. Twenty focused semantic-model tests pass. Task 2.1.1 remains open under the change-level five-role acceptance boundary; no independent/private acceptance was performed.

## Progress — 2026-11-06, M1 project-boundary assessment slice

- Implemented explicit assessment invariants: declaration and candidate kinds, resolved/ambiguous/unresolved candidate cardinalities, same-declaration-and-rule supersedes, and acyclic in-bundle lineage. Added tests for all three valid states, invalid cardinalities, incompatible rule lineage, cycles, and the valid lineage case. Twenty-two focused semantic-model tests pass. Task 2.2.1 remains open under the change-level acceptance boundary; no independent/private acceptance was performed.

## Progress — 2026-11-06, M1 evidence and coverage slice

- Implemented caller-supplied observation validation without source reads/network access, including unchecked gaps, verified digest matching, mismatch errors, evidence references, and malformed/duplicate observation rejection. Coverage now checks evidence references, complete-vs-gap consistency, same-selector/subject supersedes, resolved diagnostic keys, and acyclic lineage. Twenty-six focused semantic-model tests pass. Task 3.1.1 remains open under the change-level acceptance boundary; external tool-output attachment persistence is not represented by this wire bundle and was not claimed.

## Progress — 2026-11-06, M1 query integration

- Added `project_query_to_m1` to adapt current `project.name`, `project.language_declared`, and `workspace.member` query facts into the fixed M1 bundle, with shared Project identity, NativeWorkspace-to-PackageSpecification roles, evidence spans, observations, and coverage. It checks the project tree digest before and after projection. Thirty focused M1 tests pass. A real Click query produced two E0 facts that passed M1 validation with no diagnostics. A real regex workspace query returned the explicit `TOOL_UNAVAILABLE:cargo` gap, so the generated coverage remains incomplete. This is developer-side integration evidence, not independent/private acceptance.

## Progress — 2026-11-06, M1 single-valued claim conflicts

- The validator now compares `project.name` only within the same subject, claim mode, and condition. Different names remain in the bundle with paired conflict diagnostics, `valid=true`, and `consistency=conflicting`; declaration and interpretation claims are not compared. Thirty-one focused semantic-model tests pass. Wider context and multi-predicate conflict rules remain outstanding.

## Progress — 2026-11-06, verified Cargo workspace projection

- The M1 adapter now captures a canonical Cargo `metadata --no-deps --offline` JSON attachment, binds membership evidence to its digest, and checks the package list against the original query before marking evidence verified. If Cargo is unavailable or the repeat differs, evidence remains unchecked. Rust 1.99.1/Cargo 1.99.1 was installed under ignored `.local/`; the real regex workspace returned seven members, one verified attachment, valid M1 records, complete coverage, and no diagnostics. The focused semantic-model suite now has 32 tests.
- Added `scripts/query_m1.py` as a direct query→M1→validation entry point. Running it against the real Click checkout emits two complete E0 facts with no attachment; against regex it emits seven workspace members and one digest-checked Cargo attachment. Both JSON responses validate and report complete coverage.

## Progress — 2026-11-06, finite condition solver foundation

- Added `src/c2s_semantic_contract/conditions.py` for Boolean and finite-enum `true`/`false`, equality/inequality, `all`/`any`, and `not`. It returns exhaustive `sat`/`unsat` results up to 4,096 assignments, concrete witnesses for `sat`, and `undetermined` for unsupported fragments, unknown domains, malformed domains, and budget overflow. Claim overlap distinguishes disjoint, conflicting, and potential conflict cases. Seven focused tests pass. This is a reusable solver foundation, not complete context-record or SemanticFactSet integration.

## Progress — 2026-11-06, contextual claim integration

- Added the separate `semantic-fact-model-1` profile with finite context domains, partial context assignments, identity-preserving reference annotations, Boolean/enum condition solving, contradiction diagnostics, and overlap-aware single-valued claim conflicts. M1 project-discovery explicitly rejects context and conditional facts. Unknown or unsupported condition reasoning remains a gap/potential conflict. Forty-six focused contract/solver tests pass; the full repository suite passes 81/81, strict OpenSpec validation 21/21, artifact hashes, Python compilation, and `git diff --check` pass.
- This remains a bounded validator over the initial M1 predicate catalog. It does not complete project-wide E0–E4 extraction, language-specific condition discovery, dependency graph validation, broader evidence completeness, or behavioral algorithm proof.

## Progress — 2026-11-06, conditional dependency cycle primitive

- Added `diagnose_conditional_cycles` for explicit directed dependency graphs. It enumerates simple cycles, conjoins all edge conditions before evaluating, returns possible cycles with witnesses, proves infeasible cycles only by exhaustive finite-domain solving, and preserves unknown/source expressions and original edges. Tests cover mutually exclusive shared enum values, a satisfiable witness, and unsupported source conditions. This primitive is not yet wired to dependency records in `SemanticFactSet`, and it does not infer build-system violations.

## Progress — 2026-11-06, dependency records

- Extended the full semantic profile with separate dependency requirement and resolution records. Validation checks registered consumer/provider references, evidence references, resolution-to-requirement links, resolved/ambiguous/unresolved provider cardinality, duplicate record IDs, and condition consistency with consumer context. `scopePosition` remains orthogonal to requirement identity and resolution status. Added coverage for a valid out-of-scope resolved provider, cardinality rejection, and contradictory conditions. Requirements remain explicit inputs: project metadata is not yet projected into these records, and the cycle primitive is not yet wired to them.

## Progress — 2026-11-06, dependency-cycle integration

- `validate_model` now builds separate candidate graphs per explicit resolution configuration and attaches conditional cycle analysis to its result. It joins requirement conditions across each candidate cycle, reports infeasible/possible/undetermined distinctly, and never treats a possible cycle as a contract/build error. Enumeration has explicit cycle/search budgets; budget exhaustion and unsupported cycle conditions surface as gaps. Integration regression confirms mutually exclusive edges remain an infeasible candidate cycle while the dependency records and contract stay valid.

## Progress — 2026-11-06, claim modality and derivation links

- Expanded the full-profile fact contract to the six distinct claim modes in the design, per-evidence `Supports`/`Refutes`/`Limits` links, and optional rule-backed derivations. Validation checks evidence and premise references and rejects derivation cycles. M1 remains restricted to its two claim modes and unqualified evidence IDs. These records preserve caller assertions; they do not infer runtime observation or prove truth.

## Progress — 2026-11-06, bounded negative claims

- Added explicit positive/negative polarity and a finite negative-closure basis restricted to enumerated input or registered catalog membership checks. Validation requires nonempty unique input IDs, exactly one result per listed input, a matching fact condition, human review, no unresolved gaps, and no matching item. M1 rejects negative claims. Tests verify missing closure evidence and incomplete enumeration fail while a reviewed exhaustive record is structurally accepted. This checks only the submitted record; it cannot prove the caller's input list is objectively exhaustive.

## Progress — 2026-11-06, three-valued condition evaluation

- Added a separate `evaluate_condition` API using Kleene `true`/`false`/`unknown` results under partial assignments. Missing assignments return unknown, decisive `false` in `all` and decisive `true` in `any` dominate unknown children, and empty All/Any follow Boolean identity. The existing bounded satisfiability solver remains independent. This completes the bounded condition/cycle validator slice represented by task 2.3; language-specific extraction and broader project semantic extraction remain open.

## Progress — 2026-11-06, semantic acquisition and presentation state

- Added a separate `semanticStates` record for `obtained`/`not_acquired`/`unsupported`/`not_applicable` and `ref_only`/`expanded`. States reference optional subject/predicate scope, conditions, acquired fact IDs, evidence, and diagnostics. Unavailable states require a gap and cannot claim facts; not-applicable requires rationale and evidence; obtained fact links must match the declared scope. Acquired-but-not-expanded is valid and does not imply nonexistence. This reports the supplied selector's state and does not prove broader completeness.
