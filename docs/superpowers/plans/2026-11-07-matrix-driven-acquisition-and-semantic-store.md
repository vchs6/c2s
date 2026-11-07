# Matrix-Driven Acquisition and Semantic Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make semantic acquisition select tested tool/parser combinations from a machine-readable capability matrix and persist their normalized semantic bundles through an identity- and evidence-preserving SQLite store.

**Architecture:** Keep tool capability, installed/version/platform evidence, and parser readiness in one versioned registry consumed by a deterministic set-cover selector and adapter runner. Normalize accepted outputs into the existing M1 bundle contract; store registrations, facts, evidence, coverage, assessments, artifacts, sessions, and receipts as a self-consistent transactional unit with stable identity and evidence references.

**Tech Stack:** Python 3 standard library, SQLite, existing JSON semantic-model schema and validators, existing Python/Rust acquisition frontends and Code Review Graph parser.

**Spec:** `openspec/changes/survey-semantic-acquisition-capabilities/design.md`; `openspec/changes/design-incremental-semantic-fact-storage/design.md`; `openspec/changes/define-layered-semantic-fact-model/design.md`.

## Global Constraints

- Preserve the source project and store only outside its root.
- Select only registered parsers with successful validation evidence; unknown host/target/tool state remains unavailable, not implicitly supported.
- Validate evidence-file existence in checkout/release checks, not at runtime; installed packages must not depend on source test or research-document paths.
- A tool's output is a candidate source, not semantic truth; keep evidence, omissions, unresolved bindings, and conflicts.
- Preserve subject identity `{authority, domainId, localId}`; never use paths, names, hashes, or tool node IDs as semantic identity.
- Use Python 3 for repository-owned scripts and tests; no new third-party runtime dependency.
- Shared-workspace implementation tests are not blind/private acceptance.

## Review Focus

- Partial or malformed tool output must not light a parser or claim complete coverage.
- Multiple tools covering the same need must be deduplicated without discarding independent evidence.
- Complementary tools must be selected when one tool cannot cover all requested facts.
- Same operation ID with different content must be rejected; same fact with new evidence must merge without copying the subject.
- Failed commits and unresolved references must not expose partial bundles or masquerade as successful persistence.

---

### Task 1: Matrix-driven capability selection, parser readiness, and execution

**Authoritative task:** `survey-semantic-acquisition-capabilities/tasks.md` M1 1.1.1, with its 3.1.1/3.2.1 evidence dependencies; continue to report incomplete evidence as such.

**Files:**
- Create: `skill/src/c2s_skill/capability_matrix.py`
- Create: `skill/contracts/tool-capabilities.json`
- Modify: `skill/src/c2s_skill/query.py`
- Modify: `skill/src/c2s_skill/__main__.py`
- Test: `skill/tests/test_capability_selection.py`
- Modify: `skill/README.md`

**Interfaces:**
- `ToolCapability` records stable tool/parser IDs, version constraint, host/target applicability, provided semantic selectors, readiness evidence, and parser entrypoint.
- `select_tools(needs, matrix, environment) -> Selection` returns the smallest deterministic eligible tool set covering the requested capabilities, plus uncovered needs and reasons.
- `execute_selection(selection, request, project) -> AcquisitionBatch` invokes registered adapters, parses actual tool output, and preserves per-source evidence and gaps.
- Matrix entries marked ready are accepted only if parser tests and a source-bound validation receipt pass; candidate-only tools remain unlit.

- [x] Write failing tests for complementary coverage, deterministic minimal set, unknown host exclusion, and unlit/malformed parser refusal; existing real-project query tests cover Python/Rust/Cargo execution.
- [x] Run the selector tests in RED/GREEN order; initial failures confirmed the missing selector module before implementation.
- [x] Implement the matrix registry/selector and adapt public query selection; selected native parsers and Cargo adapters execute from the selection.
- [x] Route a version-pinned Code Review Graph 2.3.9 structured response through its matrix-selected parser and verify source-mapped call evidence plus freshness gaps.
- [x] Run targeted and full Skill tests; matrix entries reference checked-in parser tests/evidence, and candidate-only tools remain unlit.

### Task 2: M1 semantic bundle canonicalization and transactional SQLite storage

**Authoritative task:** `design-incremental-semantic-fact-storage/tasks.md` M1 1.1.1 and 2.1.1.

**Files:**
- Create: `skill/src/c2s_skill/semantic_store.py`
- Modify: `skill/src/c2s_skill/store.py` only to distinguish query cache from semantic fact repository and route the public `--store` contract correctly.
- Modify: `skill/src/c2s_skill/query.py` and `skill/src/c2s_skill/__main__.py` to persist and reread validated semantic bundles.
- Test: `skill/tests/test_semantic_store.py`
- Modify: `skill/README.md`

**Interfaces:**
- `fact_key_m1(fact) -> str` compares predicate, complete subject identity, normalized value, claim mode, and condition; it excludes record ID and evidence IDs.
- `canonicalize_m1(session, stored, pending, artifacts) -> M1Read` merges equivalent registrations/evidence/facts and rewrites every internal reference to canonical IDs without writing.
- `read_m1(store, analysis_id) -> M1Read`, `commit_m1(store, candidate) -> M1Receipt`, and `lookup_m1(store, analysis_id, operation_id) -> M1Receipt` implement the existing design contract.
- SQLite commits the self-consistent bundle, artifact bytes, session, and idempotency receipt in one transaction; successful receipt is followed by canonical read-back before results are returned as persisted.

- [x] Write failing tests for fact equivalence, evidence-only additions, identity preservation, conflict retention, same-operation idempotency, mismatched retry, external-store boundary, atomic rollback, and canonical read-back.
- [x] Run the semantic-store tests in RED/GREEN order; initial failures confirmed the missing module and contract wiring.
- [x] Implement deterministic canonicalization and normalized SQLite tables/transactions using standard-library `sqlite3`.
- [x] Integrate M1 `--store` separately from query-result `--cache`; reject unsupported code-level selectors instead of silently dropping them.
- [x] Run targeted and full Skill/repository/OpenSpec/artifact checks; shared-workspace tests are not private acceptance.

