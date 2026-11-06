# Semantic Model Rules — M1 identity slice

Contract version: `1.0.0`  
Profile: `m1-project-discovery-1`

## Identity and subject references

A subject identity is the explicit triple `{authority, domainId, localId}`. Its kind is stored beside the identity in `M1SubjectRef`, not encoded in the identity. E0–E4 layer, path, source name, line/byte location, commit, content digest, parser node ID, and graph-tool ID are not identity components.

Within one identity domain, one identity has one subject kind. Reusing an identity with a different kind is a contract error; the validator preserves the conflicting records in its diagnostics rather than silently rewriting the kind. A path or name may be used as evidence or a lookup key, but cannot by itself establish identity.

`M1Registration.sourceKey` locates a source declaration within the fixed input and acquisition profile. It is not emitted as the subject identity. Calling `register_m1` again with the same domain, source key, and kind returns the existing identity and unions evidence IDs. Reusing that source key with another kind or domain returns `CONTRACT_INVALID`; the registry must not guess continuity or allocate a replacement identity.

A new registration receives an explicit UUID local identifier under authority `c2s-local` and the caller-provided identity domain. Moving a checkout, adding evidence, or resolving a project-boundary assessment does not re-key the subject. M1 references carry no context reference; contextual interpretation uses the separate `semantic-fact-model-1` profile. There, `contextRef` annotates a reference without changing its identity. Contexts are partial assignments over registered finite Boolean or enum keys; absent keys remain unconstrained. Fact conditions and subject/value contexts are checked together. Contradictions are errors (`CTX_CONTRADICTION`); unsupported conditions, unknown keys, and over-budget searches remain explicit gaps. Single-valued claims conflict only when their conditions can overlap; unsupported overlap yields `POTENTIAL_CONFLICT`.

## Structural validation boundary

`validate_model` runs four dependent stages in order: fixed catalog integrity, versioned wire structure, internal subject/evidence references, then the available M1 invariants. A failed stage leaves its dependent stages `not_run`; reference diagnostics retain identity/source conflicts and related record references. `valid` reports contract errors only. Different values for a single-valued predicate in the same subject/claim-mode/condition are preserved as paired `conflict` diagnostics and return `valid=true`, `consistency=conflicting`; otherwise a successful checked subset has `invariants=partial`, `consistency=undetermined`. Neither result establishes source truth, project ownership, semantic completeness, or runtime behavior. Evidence-source observation checks and broader cross-fact rules remain outside this M1 slice.

## Project-boundary assessment invariants

An assessment declaration must reference a `SourceDeclaration`, and every candidate must reference a `Project`. `resolved` has exactly one candidate, `ambiguous` has at least two, and `unresolved` has none. An assessment may supersede only assessments with the same declaration identity and `ruleId`; the in-bundle supersedes graph must be acyclic. These constraints validate explicit assessments only: package or workspace membership does not infer project ownership.

## Dependency requirement and resolution records

The `semantic-fact-model-1` profile can retain `dependencies` separately from `dependencyResolutions`. A requirement records its consumer, purpose, stage, path/version selectors, condition, and evidence; resolution records candidates/status, configuration, visibility, and `scopePosition`. `scopePosition` is independent of dependency identity and resolution status. Providers and consumers must resolve to registered subject identities. A resolved record has exactly one provider, ambiguous has at least two, and unresolved has none. Requirements remain present when no resolution exists. This initial contract does not infer requirements from package metadata or decide whether a project-level dependency cycle is an error.

## Evidence and coverage invariants

`source_observations` is caller-supplied and is never obtained by reading files or contacting a network. A missing observation or `unchecked` status yields a `gap` diagnostic and does not make the contract invalid. `verified` requires an observed SHA-256 equal to the evidence digest; `mismatch` requires an observed, different digest and produces an `INPUT_MISMATCH` contract error. Observation entries must be unique and reference evidence in the bundle. A coverage record marked complete cannot carry gap/error diagnostics or cite unchecked evidence. In-bundle coverage supersedes links must preserve selector and subject identity, resolved diagnostic keys use compact JSON `[code,recordId,path]` values referring to gap/error diagnostics on a superseded record, and lineage must be acyclic.

In `semantic-fact-model-1`, facts can distinguish `declaration`, `specification`, `static_may`, `static_must`, `observation`, and `interpretation`; these modes are not ranked as truth. `evidenceRefs` attach each evidence ID with a `Supports`, `Refutes`, or `Limits` role. Optional derivations name a rule and premise fact IDs; missing premises are reference errors and derivation cycles are invariant errors. Neither support role nor derivation establishes source truth. The M1 project-discovery profile remains limited to declaration/interpretation and unqualified evidence IDs.

## Finite condition reasoning (implementation slice)

`src/c2s_semantic_contract/conditions.py` supports `true`/`false`, `eq`/`neq`, `all`/`any`, and `not` over caller-declared finite Boolean or enum domains. It exhaustively checks up to 4,096 assignments and returns a witness for `sat`; unsupported expressions, unknown domains, malformed domains, and larger products return `undetermined`, never `false`. `classify_claim_overlap` distinguishes disjoint conditions, confirmed conflicting values, and potential conflicts. The full-profile contract integrates contexts and conditions for the initial catalog; language-specific condition extraction and broader predicate semantics remain outstanding. The bounded solver does not prove behavior semantics.

`validate_model` builds configuration-separated candidate graphs from explicit dependency resolutions and reports cycle analysis separately in `dependencyCycles`; a possible project cycle is not itself a contract error or a build-rule violation. `diagnose_conditional_cycles` enumerates simple directed cycles and evaluates each cycle's edge conditions jointly. It returns possible cycles with witnesses, infeasible cycles after exhaustive finite-domain reasoning, and undetermined cycles with reasons; the original graph is returned unchanged. Enumeration is bounded by 4,096 cycles and a bounded search budget; exhaustion is an explicit gap and leaves unvisited cycles unknown.
