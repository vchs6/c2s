# Semantic Model Contract

## Status and scope

The public M1 slice is version `1.0.0`, profile `m1-project-discovery-1`. It establishes explicit subject identity and a bounded JSON exchange shape for registrations, assessments, facts, evidence, coverage, and diagnostics. It does not yet implement the complete E0–E4 model or prove that claims match source behavior.

## Identity language

A **Subject** is an independently referable object. Its identity is `{authority, domainId, localId}`; its `kind` is carried by a typed `M1SubjectRef`. The identity does not contain a path, name, layer, commit, content hash, or tool-generated node identifier. This lets evidence move or gain corroboration without changing subject identity.

A **sourceKey** is an acquisition-local lookup key for reconnecting a source declaration with its registered subject. `register_m1` reuses the registered identity for a repeated source key and merges evidence IDs. A source-key/kind or source-key/domain conflict is rejected as `CONTRACT_INVALID` rather than resolved by guessing.

The M1 subject kinds are `Project`, `PackageSpecification`, `NativeWorkspace`, and `SourceDeclaration`. They are distinct concepts: package/workspace membership does not itself create a Project identity, and a source declaration is not promoted to a Project. M1 references do not carry interpretation context; contextual claims are outside this slice.

## Validation and evidence boundary

`contracts/semantic-model/fact.schema.json` provides JSON Schema 2020-12 structural validation. `src/c2s_semantic_contract/validation.py` adds local reference and identity checks. Contract validity is not source truth. Evidence observations, the closed predicate catalog, project-mapping rules, cross-claim conflict analysis, and later E1–E4 semantics remain separate implementation tasks. Shared-workspace developer tests are not independent or private acceptance evidence.
