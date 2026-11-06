# Semantic Model Rules — M1 identity slice

Contract version: `1.0.0`  
Profile: `m1-project-discovery-1`

## Identity and subject references

A subject identity is the explicit triple `{authority, domainId, localId}`. Its kind is stored beside the identity in `M1SubjectRef`, not encoded in the identity. E0–E4 layer, path, source name, line/byte location, commit, content digest, parser node ID, and graph-tool ID are not identity components.

Within one identity domain, one identity has one subject kind. Reusing an identity with a different kind is a contract error; the validator preserves the conflicting records in its diagnostics rather than silently rewriting the kind. A path or name may be used as evidence or a lookup key, but cannot by itself establish identity.

`M1Registration.sourceKey` locates a source declaration within the fixed input and acquisition profile. It is not emitted as the subject identity. Calling `register_m1` again with the same domain, source key, and kind returns the existing identity and unions evidence IDs. Reusing that source key with another kind or domain returns `CONTRACT_INVALID`; the registry must not guess continuity or allocate a replacement identity.

A new registration receives an explicit UUID local identifier under authority `c2s-local` and the caller-provided identity domain. Moving a checkout, adding evidence, or resolving a project-boundary assessment does not re-key the subject. M1 references carry no context reference; contextual interpretation belongs to a later contract slice.

## Structural validation boundary

`validate_model` runs four dependent stages in order: fixed catalog integrity, versioned wire structure, internal subject/evidence references, then the available M1 invariants. A failed stage leaves its dependent stages `not_run`; reference diagnostics retain identity/source conflicts and related record references. A successful result means only that the checked contract rules hold (`valid=true`, `invariants=partial`); `consistency` remains `undetermined` and does not establish source truth, project ownership, semantic completeness, or runtime behavior. Evidence-source observation checks and broader cross-fact rules remain outside this M1 slice.
