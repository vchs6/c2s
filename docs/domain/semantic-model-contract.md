# Semantic Model Contract

## Status and scope

Version `1.0.0` exposes two profiles: `m1-project-discovery-1` remains the narrow project/workspace identity contract, and `semantic-fact-model-1` adds contextual claims, finite conditions, dependencies/resolutions, evidence roles, derivations, semantic acquisition/presentation states, and an expanded closed predicate catalog. `project_query_to_semantic_model` projects every fact kind currently returned by the Python/Rust analyzer into that expanded profile. Fixed Click and regex checkouts exercise 23,779 and 54,313 returned facts respectively. Those totals describe the analyzer's supported acquisition surface, not all possible project semantics. Workspace metadata unavailable from Cargo remains a gap. The model validates shape, references, and declared invariants; it does not prove source truth, complete E0–E4 extraction, or runtime behavior.

## Identity language

A **Subject** is an independently referable object. Its identity is `{authority, domainId, localId}`; its `kind` is carried by a typed `M1SubjectRef`. The identity does not contain a path, name, layer, commit, content hash, or tool-generated node identifier. This lets evidence move or gain corroboration without changing subject identity.

A **sourceKey** is an acquisition-local lookup key for reconnecting a source declaration with its registered subject. `register_m1` reuses the registered identity for a repeated source key and merges evidence IDs. A source-key/kind or source-key/domain conflict is rejected as `CONTRACT_INVALID` rather than resolved by guessing.

The M1 subject kinds are `Project`, `PackageSpecification`, `NativeWorkspace`, and `SourceDeclaration`. They are distinct concepts: package/workspace membership does not itself create a Project identity, and a source declaration is not promoted to a Project. M1 references do not carry interpretation context; contextual claims are outside this slice.

## Validation and evidence boundary

`contracts/semantic-model/fact.schema.json` provides JSON Schema 2020-12 structural validation for both profiles. `src/c2s_semantic_contract/validation.py` adds local reference, catalog, identity, condition, dependency, coverage, derivation, and claim consistency checks. `project_query_to_semantic_model` rechecks the scanned source fingerprint, hashes source evidence, preserves original acquisition metadata, and does not turn empty results into negative claims. Contract validity is not source truth; coverage is scoped to the submitted selector and inventory. Full language-mechanism mapping, the complete engineering/build-delivery model, broader composition/reference rules, query execution guarantees, and runtime behavior remain implementation tasks. Shared-workspace tests are implementation evidence, not independent acceptance.
