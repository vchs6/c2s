# Semantic Model Rules — M1 identity slice

Contract version: `1.0.0`  
Profile: `m1-project-discovery-1`

## Identity and subject references

A subject identity is the explicit triple `{authority, domainId, localId}`. Its kind is stored beside the identity in `M1SubjectRef`, not encoded in the identity. E0–E4 layer, path, source name, line/byte location, commit, content digest, parser node ID, and graph-tool ID are not identity components.

Within one identity domain, one identity has one subject kind. Reusing an identity with a different kind is a contract error; the validator preserves the conflicting records in its diagnostics rather than silently rewriting the kind. A path or name may be used as evidence or a lookup key, but cannot by itself establish identity.

`M1Registration.sourceKey` locates a source declaration within the fixed input and acquisition profile. It is not emitted as the subject identity. Calling `register_m1` again with the same domain, source key, and kind returns the existing identity and unions evidence IDs. Reusing that source key with another kind or domain returns `CONTRACT_INVALID`; the registry must not guess continuity or allocate a replacement identity.

A new registration receives an explicit UUID local identifier under authority `c2s-local` and the caller-provided identity domain. Moving a checkout, adding evidence, or resolving a project-boundary assessment does not re-key the subject. M1 references carry no context reference; contextual interpretation belongs to a later contract slice.

## Structural validation boundary

`validate_model` runs four dependent stages in order: fixed catalog integrity, versioned wire structure, internal subject/evidence references, then the available M1 invariants. A failed stage leaves its dependent stages `not_run`; reference diagnostics retain identity/source conflicts and related record references. `valid` reports contract errors only. Different values for a single-valued predicate in the same subject/claim-mode/condition are preserved as paired `conflict` diagnostics and return `valid=true`, `consistency=conflicting`; otherwise a successful checked subset has `invariants=partial`, `consistency=undetermined`. Neither result establishes source truth, project ownership, semantic completeness, or runtime behavior. Evidence-source observation checks and broader cross-fact rules remain outside this M1 slice.

## Project-boundary assessment invariants

An assessment declaration must reference a `SourceDeclaration`, and every candidate must reference a `Project`. `resolved` has exactly one candidate, `ambiguous` has at least two, and `unresolved` has none. An assessment may supersede only assessments with the same declaration identity and `ruleId`; the in-bundle supersedes graph must be acyclic. These constraints validate explicit assessments only: package or workspace membership does not infer project ownership.

## Evidence and coverage invariants

`source_observations` is caller-supplied and is never obtained by reading files or contacting a network. A missing observation or `unchecked` status yields a `gap` diagnostic and does not make the contract invalid. `verified` requires an observed SHA-256 equal to the evidence digest; `mismatch` requires an observed, different digest and produces an `INPUT_MISMATCH` contract error. Observation entries must be unique and reference evidence in the bundle. A coverage record marked complete cannot carry gap/error diagnostics or cite unchecked evidence. In-bundle coverage supersedes links must preserve selector and subject identity, resolved diagnostic keys use compact JSON `[code,recordId,path]` values referring to gap/error diagnostics on a superseded record, and lineage must be acyclic.

## Finite condition reasoning (implementation slice)

`src/c2s_semantic_contract/conditions.py` supports `true`/`false`, `eq`/`neq`, `all`/`any`, and `not` over caller-declared finite Boolean or enum domains. It exhaustively checks up to 4,096 assignments and returns a witness for `sat`; unsupported expressions, unknown domains, malformed domains, and larger products return `undetermined`, never `false`. `classify_claim_overlap` distinguishes disjoint conditions, confirmed conflicting values, and potential conflicts. This solver is a reusable implementation slice; full context records and integration into the complete SemanticFactSet remain outstanding.
