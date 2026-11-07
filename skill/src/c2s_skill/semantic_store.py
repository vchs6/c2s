"""SQLite repository for M1 and full layered semantic-fact bundles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import UUID


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _empty_bundle() -> dict:
    return {"version": "1.0.0", "profile": "m1-project-discovery-1", "registrations": [],
            "assessments": [], "facts": [], "evidence": [], "coverage": [], "diagnostics": []}


def _identity_key(ref: dict) -> str:
    identity = ref["identity"]
    return _json({"authority": identity["authority"], "domainId": identity["domainId"],
                  "localId": identity["localId"]})


def fact_key_m1(fact: dict) -> str:
    """Return the contract comparison key, excluding fact and evidence IDs."""
    subject = fact.get("subject", {})
    identity = subject.get("identity", {})
    return _json({"predicate": fact.get("predicate"),
                  "subject": {key: identity.get(key) for key in ("authority", "domainId", "localId")},
                  "value": fact.get("value"), "claimMode": fact.get("claimMode"),
                  "condition": fact.get("condition")})


def fact_key_semantic(fact: dict) -> str:
    """Comparison identity for a layered claim, excluding presentation/evidence identity."""
    omitted = {"factId", "evidenceIds", "evidenceRefs", "derivation"}
    metadata = fact.get("sourceMetadata")
    if isinstance(metadata, dict):
        metadata = {key: value for key, value in metadata.items()
                    if key not in {"evidenceIncluded", "text"}}
    value = {key: item for key, item in fact.items() if key not in omitted | {"sourceMetadata"}}
    if metadata is not None:
        value["sourceMetadata"] = metadata
    return _json(value)


_FULL_COLLECTIONS = ("registrations", "assessments", "facts", "evidence", "coverage",
                     "dependencies", "dependencyResolutions", "semanticStates", "diagnostics",
                     "contextDomains", "contexts")


def _semantic_references(collection: str, record: dict) -> list[tuple[str, str, str]]:
    """Extract typed cross-record edges so the normalized store can audit bundle links."""
    refs = []
    def add(field: str, target: str, values):
        for value in values if isinstance(values, list) else [values]:
            if isinstance(value, str):
                refs.append((field, target, value))
    if collection in {"registrations", "facts", "assessments", "coverage", "dependencies",
                      "dependencyResolutions", "semanticStates"}:
        add("evidenceIds", "evidence", record.get("evidenceIds", []))
    if collection == "facts":
        add("contextIds", "contexts", record.get("contextIds", []))
        for item in record.get("evidenceRefs", []):
            add("evidenceRefs", "evidence", item.get("evidenceId"))
    elif collection == "assessments":
        add("supersedes", "assessments", record.get("supersedes", []))
    elif collection == "coverage":
        add("supersedes", "coverage", record.get("supersedes", []))
    elif collection == "dependencyResolutions":
        add("dependencyId", "dependencies", record.get("dependencyId"))
    elif collection == "semanticStates":
        add("factIds", "facts", record.get("factIds", []))
    elif collection == "evidence":
        add("artifactId", "artifacts", record.get("artifactId"))
    if collection in {"assessments", "coverage", "semanticStates", "diagnostics"}:
        diagnostics = record.get("diagnostics", [])
        for item in diagnostics:
            if isinstance(item, dict) and item.get("recordId"):
                add("diagnostic.recordId", "records", item["recordId"])
    if collection == "diagnostics" and record.get("recordId"):
        add("recordId", "records", record["recordId"])
    return refs


def canonicalize_semantic(bundle: dict) -> dict:
    """Return a stable, complete full-profile bundle without dropping any model collection."""
    if bundle.get("profile") != "semantic-fact-model-1" or bundle.get("version") != "1.0.0":
        raise ValueError("only semantic-fact-model-1 version 1.0.0 bundles are supported")
    result = {"version": "1.0.0", "profile": "semantic-fact-model-1"}
    for name in _FULL_COLLECTIONS:
        collection = bundle.get(name, [])
        if not isinstance(collection, list):
            raise ValueError(f"{name} must be an array")
        result[name] = sorted(collection, key=_json)
    return result


def _merge_semantic_bundles(old: dict, new: dict) -> dict:
    """Accumulate independently requested selector facts into one full-profile bundle."""
    if old.get("profile") != "semantic-fact-model-1":
        old = {"version": "1.0.0", "profile": "semantic-fact-model-1",
               **{name: [] for name in _FULL_COLLECTIONS}}
    result = {"version": "1.0.0", "profile": "semantic-fact-model-1"}
    fact_id_map: dict[str, str] = {}
    id_fields = {"registrations": "sourceKey", "assessments": "assessmentId", "facts": "factId",
        "evidence": "evidenceId", "coverage": "coverageId", "dependencies": "dependencyId",
        "dependencyResolutions": "resolutionId", "semanticStates": "stateId",
        "diagnostics": None, "contextDomains": "keyId", "contexts": "contextId"}
    for name in _FULL_COLLECTIONS:
        by_key = {}
        for record in old.get(name, []) + new.get(name, []):
            field = id_fields[name]
            key = fact_key_semantic(record) if name == "facts" else (record[field] if field else _json(record))
            previous = by_key.get(key)
            if previous is not None and name == "registrations":
                merged = dict(previous)
                merged["evidenceIds"] = sorted(set(previous.get("evidenceIds", [])) |
                                               set(record.get("evidenceIds", [])))
                if _json({k: v for k, v in previous.items() if k != "evidenceIds"}) != _json(
                        {k: v for k, v in record.items() if k != "evidenceIds"}):
                    raise ValueError(f"conflicting registration records share source key {key!r}")
                by_key[key] = merged
            elif previous is not None and name == "facts":
                merged = dict(previous)
                canonical_id = min(previous["factId"], record["factId"])
                fact_id_map[previous["factId"]] = canonical_id
                fact_id_map[record["factId"]] = canonical_id
                merged["factId"] = canonical_id
                for list_field in ("evidenceIds",):
                    merged[list_field] = sorted(set(previous.get(list_field, [])) | set(record.get(list_field, [])))
                refs = {(_json(ref), ref.get("role")): ref
                        for ref in previous.get("evidenceRefs", []) + record.get("evidenceRefs", [])}
                if refs:
                    merged["evidenceRefs"] = sorted(refs.values(), key=_json)
                by_key[key] = merged
            elif previous is None:
                by_key[key] = record
            elif _json(previous) != _json(record):
                raise ValueError(f"conflicting {name} records share identity {key!r}")
        result[name] = sorted(by_key.values(), key=_json)
    if fact_id_map:
        for state in result["semanticStates"]:
            state["factIds"] = sorted({fact_id_map.get(value, value) for value in state.get("factIds", [])})
        for record in result["assessments"] + result["coverage"] + result["diagnostics"]:
            if record.get("recordId") is not None:
                record["recordId"] = fact_id_map.get(record["recordId"], record["recordId"])
    return result


def _evidence_key(evidence: dict, artifact_hashes: dict[str, str]) -> str:
    artifact_id = evidence.get("artifactId")
    return _json({"source": evidence.get("source"), "path": evidence.get("path"),
                  "artifactSha256": artifact_hashes.get(artifact_id) if artifact_id else None,
                  "sha256": evidence.get("sha256"), "startByte": evidence.get("startByte"),
                  "endByte": evidence.get("endByte"), "method": evidence.get("method"),
                  "toolName": evidence.get("toolName"), "toolVersion": evidence.get("toolVersion")})


def _merge_records(existing: list[dict], incoming: list[dict], id_field: str,
                   key_function) -> tuple[list[dict], dict[str, str]]:
    values: dict[str, dict] = {}
    old_ids: set[str] = set()
    id_map: dict[str, str] = {}
    for record in existing:
        key = key_function(record)
        record_id = record[id_field]
        old_ids.add(record_id)
        if key not in values:
            values[key] = dict(record)
        else:
            current_id = values[key][id_field]
            canonical_id = min(current_id, record_id)
            values[key] = {**values[key], id_field: canonical_id}
            id_map[record_id] = canonical_id
            id_map[current_id] = canonical_id
    for record in incoming:
        key = key_function(record)
        record_id = record[id_field]
        if key in values:
            canonical_id = values[key][id_field]
            if record_id != canonical_id:
                id_map[record_id] = canonical_id
        else:
            values[key] = dict(record)
    if id_field == "factId":
        evidence_by_key: dict[str, set[str]] = {}
        for record in existing + incoming:
            evidence_by_key.setdefault(key_function(record), set()).update(record.get("evidenceIds", []))
        for key, record in values.items():
            record["evidenceIds"] = sorted(evidence_by_key[key])
    result = sorted(values.values(), key=lambda item: item[id_field])
    canonical = {key_function(item): item[id_field] for item in result}
    for record in existing + incoming:
        id_map.setdefault(record[id_field], canonical[key_function(record)])
    return result, id_map


def _remap_list(record: dict, field: str, id_map: dict[str, str]) -> dict:
    if field not in record:
        return record
    return {**record, field: sorted({id_map.get(value, value) for value in record[field]})}


def _remap_assessment(record: dict, id_map: dict[str, str]) -> dict:
    value = _remap_list(record, "evidenceIds", id_map)
    value = _remap_list(value, "supersedes", id_map)
    value["diagnostics"] = [dict(item, recordId=id_map.get(item.get("recordId"), item.get("recordId")))
                            if item.get("recordId") is not None else item
                            for item in value.get("diagnostics", [])]
    return value


def _record_identity(record: dict, id_field: str) -> str:
    return _json({key: value for key, value in record.items() if key != id_field})


def _merge_registrations(existing: list[dict], incoming: list[dict], evidence_map: dict[str, str]) -> list[dict]:
    merged: dict[str, dict] = {}
    for record in existing + incoming:
        source_key = record["sourceKey"]
        evidence_ids = sorted({evidence_map.get(value, value) for value in record["evidenceIds"]})
        normalized = {**record, "evidenceIds": evidence_ids}
        previous = merged.get(source_key)
        if previous is not None and (previous["ref"] != normalized["ref"]):
            raise ValueError(f"sourceKey {source_key!r} is already registered with another identity")
        if previous is None:
            merged[source_key] = normalized
        else:
            previous["evidenceIds"] = sorted(set(previous["evidenceIds"]) | set(evidence_ids))
    return [merged[key] for key in sorted(merged)]


def canonicalize_m1(session: dict, stored: dict, pending: dict,
                    artifacts: list[dict]) -> dict:
    """Merge a validated M1 candidate with stored history without writing it."""
    old_bundle = stored.get("bundle") if isinstance(stored, dict) else None
    old_bundle = old_bundle if isinstance(old_bundle, dict) else _empty_bundle()
    if pending.get("profile") != "m1-project-discovery-1" or pending.get("version") != "1.0.0":
        raise ValueError("only M1 version 1.0.0 bundles can be canonicalized")
    if old_bundle.get("profile") not in {None, "m1-project-discovery-1"}:
        raise ValueError("stored bundle profile does not match M1")

    all_artifacts = list(stored.get("artifacts", [])) + list(artifacts)
    artifacts_by_hash: dict[str, dict] = {}
    artifact_map: dict[str, str] = {}
    for artifact in all_artifacts:
        content = artifact.get("content")
        if not isinstance(content, str):
            raise ValueError("M1 artifact content must be text")
        actual_hash = _sha(content.encode("utf-8"))
        if actual_hash != artifact.get("sha256"):
            raise ValueError("M1 artifact SHA-256 does not match its content")
        previous = artifacts_by_hash.get(actual_hash)
        canonical_id = previous["artifactId"] if previous else actual_hash
        artifact_map[artifact["artifactId"]] = canonical_id
        artifacts_by_hash[actual_hash] = {"artifactId": canonical_id, "mediaType": "application/json",
                                           "sha256": actual_hash, "content": content}
    canonical_artifacts = [artifacts_by_hash[key] for key in sorted(artifacts_by_hash)]
    artifact_hashes = {item["artifactId"]: item["sha256"] for item in canonical_artifacts}

    old_evidence = [dict(item, artifactId=artifact_map.get(item.get("artifactId"), item.get("artifactId")))
                    for item in old_bundle.get("evidence", [])]
    new_evidence = [dict(item, artifactId=artifact_map.get(item.get("artifactId"), item.get("artifactId")))
                    for item in pending.get("evidence", [])]
    evidence, evidence_map = _merge_records(
        old_evidence, new_evidence, "evidenceId", lambda item: _evidence_key(item, artifact_hashes))

    registration_records = _merge_registrations(old_bundle.get("registrations", []),
        pending.get("registrations", []), evidence_map)
    old_facts = [_remap_list(item, "evidenceIds", evidence_map) for item in old_bundle.get("facts", [])]
    new_facts = [_remap_list(item, "evidenceIds", evidence_map) for item in pending.get("facts", [])]
    facts, fact_map = _merge_records(old_facts, new_facts, "factId", fact_key_m1)

    old_assessments = [_remap_assessment(item, evidence_map) for item in old_bundle.get("assessments", [])]
    new_assessments = [_remap_assessment(item, evidence_map) for item in pending.get("assessments", [])]
    assessments, assessment_map = _merge_records(old_assessments, new_assessments, "assessmentId",
        lambda item: _record_identity(item, "assessmentId"))
    assessments = [_remap_list(item, "supersedes", assessment_map) for item in assessments]

    old_coverage = [_remap_list(item, "evidenceIds", evidence_map) for item in old_bundle.get("coverage", [])]
    new_coverage = [_remap_list(item, "evidenceIds", evidence_map) for item in pending.get("coverage", [])]
    coverage, coverage_map = _merge_records(old_coverage, new_coverage, "coverageId",
        lambda item: _record_identity(item, "coverageId"))
    coverage = [_remap_list(item, "supersedes", coverage_map) for item in coverage]

    diagnostics = []
    diagnostic_map = {}
    for item in old_bundle.get("diagnostics", []) + pending.get("diagnostics", []):
        updated = dict(item)
        if updated.get("recordId") is not None:
            updated["recordId"] = (assessment_map.get(updated["recordId"])
                                   or coverage_map.get(updated["recordId"])
                                   or fact_map.get(updated["recordId"], updated["recordId"]))
        diagnostic_map[_record_identity(updated, "__none__")] = updated
    diagnostics = [diagnostic_map[key] for key in sorted(diagnostic_map)]

    bundle = {"version": "1.0.0", "profile": "m1-project-discovery-1",
              "registrations": registration_records, "assessments": assessments, "facts": facts,
              "evidence": evidence, "coverage": coverage, "diagnostics": diagnostics}
    return {"analysisId": session["analysisId"], "session": session,
            "generation": stored.get("generation", 0) if isinstance(stored, dict) else 0,
            "bundle": bundle, "artifacts": canonical_artifacts,
            "receipts": list(stored.get("receipts", [])) if isinstance(stored, dict) else [],
            "diagnostics": []}


class SemanticFactStore:
    """External SQLite repository for typed semantic-fact bundles."""

    def __init__(self, path: Path | str):
        self.path = Path(path).resolve()

    def validate_root(self, root: Path | str) -> None:
        root = Path(root).resolve(strict=True)
        if self.path == root or root in self.path.parents:
            raise ValueError("semantic fact store must be outside the analyzed project")

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS sessions(
                analysis_id TEXT PRIMARY KEY, session_json TEXT NOT NULL, generation INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS registrations(
                analysis_id TEXT NOT NULL, source_key TEXT NOT NULL, identity_key TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(analysis_id, source_key),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS evidence(
                analysis_id TEXT NOT NULL, evidence_key TEXT NOT NULL, evidence_id TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(analysis_id, evidence_key),
                UNIQUE(analysis_id, evidence_id),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS facts(
                analysis_id TEXT NOT NULL, fact_key TEXT NOT NULL, fact_id TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(analysis_id, fact_key), UNIQUE(analysis_id, fact_id),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS assessments(
                analysis_id TEXT NOT NULL, record_key TEXT NOT NULL, assessment_id TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(analysis_id, record_key),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS coverage(
                analysis_id TEXT NOT NULL, record_key TEXT NOT NULL, coverage_id TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(analysis_id, record_key),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS diagnostics(
                analysis_id TEXT NOT NULL, record_key TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(analysis_id, record_key),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS artifacts(
                analysis_id TEXT NOT NULL, sha256 TEXT NOT NULL, artifact_id TEXT NOT NULL,
                media_type TEXT NOT NULL, content TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(analysis_id, sha256),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS receipts(
                analysis_id TEXT NOT NULL, operation_id TEXT NOT NULL, content_hash TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(analysis_id, operation_id),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS full_bundles(
                analysis_id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS semantic_records(
                analysis_id TEXT NOT NULL, collection TEXT NOT NULL, record_key TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(analysis_id, collection, record_key),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS semantic_refs(
                analysis_id TEXT NOT NULL, source_collection TEXT NOT NULL, source_id TEXT NOT NULL,
                field TEXT NOT NULL, target_collection TEXT NOT NULL, target_id TEXT NOT NULL,
                PRIMARY KEY(analysis_id, source_collection, source_id, field, target_collection, target_id),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS source_observations(
                analysis_id TEXT NOT NULL, evidence_id TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(analysis_id, evidence_id),
                FOREIGN KEY(analysis_id) REFERENCES sessions(analysis_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS semantic_query_reports(
                root TEXT NOT NULL, selector TEXT NOT NULL, source_digest TEXT NOT NULL,
                profile_digest TEXT NOT NULL, analysis_id TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(root, selector, source_digest, profile_digest));
        """)
        return connection


def _read_connection(connection: sqlite3.Connection, analysis_id: str) -> dict:
    session_row = connection.execute(
        "SELECT session_json,generation FROM sessions WHERE analysis_id=?", (analysis_id,)).fetchone()
    if session_row is None:
        return {"analysisId": analysis_id, "session": None, "generation": 0,
                "bundle": _empty_bundle(), "artifacts": [], "receipts": [], "diagnostics": []}
    session = json.loads(session_row[0])
    categories = {}
    for category in ("registrations", "evidence", "facts", "assessments", "coverage", "diagnostics"):
        rows = connection.execute(f"SELECT payload FROM {category} WHERE analysis_id=? ORDER BY rowid",
                                  (analysis_id,)).fetchall()
        categories[category] = [json.loads(row[0]) for row in rows]
    artifact_rows = connection.execute("SELECT payload FROM artifacts WHERE analysis_id=? ORDER BY sha256",
                                       (analysis_id,)).fetchall()
    receipt_rows = connection.execute("SELECT payload FROM receipts WHERE analysis_id=? ORDER BY operation_id",
                                      (analysis_id,)).fetchall()
    return {"analysisId": analysis_id, "session": session, "generation": session_row[1],
            "bundle": {"version": "1.0.0", "profile": session["profile"], **categories},
            "artifacts": [json.loads(row[0]) for row in artifact_rows],
            "receipts": [json.loads(row[0]) for row in receipt_rows], "diagnostics": []}


def read_m1(store: SemanticFactStore | Path | str, analysis_id: str) -> dict:
    repository = store if isinstance(store, SemanticFactStore) else SemanticFactStore(store)
    with repository._connect() as connection:
        result = _read_connection(connection, analysis_id)
    if result["session"] is not None:
        repository.validate_root(result["session"]["root"])
    return result


def _validate_candidate(candidate: dict, repository: SemanticFactStore) -> tuple[str, dict, str]:
    if not isinstance(candidate, dict):
        raise ValueError("M1 commit must be an object")
    session = candidate.get("session")
    required = {"analysisId", "inputId", "root", "store", "identityDomain", "profile", "host", "target", "tools"}
    if not isinstance(session, dict) or not required <= set(session):
        raise ValueError("M1 session is missing required analysis identity fields")
    try:
        for field in ("analysisId", "inputId", "identityDomain"):
            UUID(session[field])
    except (ValueError, TypeError, AttributeError):
        raise ValueError("M1 analysisId, inputId and identityDomain must be UUIDs") from None
    root = Path(session["root"]).resolve(strict=True)
    repository.validate_root(root)
    if Path(session["store"]).resolve() != repository.path:
        raise ValueError("M1 session store path does not match repository")
    if session["profile"] != "m1-project-discovery-1":
        raise ValueError("unsupported M1 session profile")
    operation_id = candidate.get("operationId")
    generation = candidate.get("expectedGeneration")
    if not isinstance(operation_id, str) or not operation_id or type(generation) is not int or generation < 0:
        raise ValueError("M1 commit requires a non-empty operation ID and non-negative generation")
    bundle = candidate.get("bundle")
    artifacts = candidate.get("artifacts")
    if not isinstance(bundle, dict) or not isinstance(artifacts, list):
        raise ValueError("M1 commit requires a bundle and artifact array")
    from c2s_semantic_contract.validation import semantic_model_catalogs, validate_model
    validation = validate_model(bundle, semantic_model_catalogs(bundle.get("profile", "")))
    if not validation["valid"]:
        raise ValueError("M1 bundle failed contract validation: " + ", ".join(
            item.get("ruleCode", "CONTRACT_INVALID") for item in validation["diagnostics"]))
    if any(item["ref"]["identity"]["domainId"] != session["identityDomain"]
           for item in bundle.get("registrations", [])):
        raise ValueError("M1 registration identity domain does not match its session")
    for artifact in artifacts:
        content = artifact.get("content") if isinstance(artifact, dict) else None
        if not isinstance(content, str) or _sha(content.encode("utf-8")) != artifact.get("sha256"):
            raise ValueError("M1 artifact content digest is invalid")
    digest = _sha(_json({"session": session, "bundle": bundle, "artifacts": artifacts}).encode("utf-8"))
    return operation_id, session, digest


def _receipt(operation_id: str, state: str, generation: int, added: list[str] | None = None,
             existing: list[str] | None = None, diagnostics: list[dict] | None = None) -> dict:
    return {"operationId": operation_id, "state": state, "generation": generation,
            "addedIds": sorted(set(added or [])), "existingIds": sorted(set(existing or [])),
            "diagnostics": diagnostics or []}


def _record_keys(bundle: dict, artifacts: list[dict] | None = None) -> dict[str, dict[str, str]]:
    artifact_hashes = {item["artifactId"]: item["sha256"] for item in (artifacts or [])}
    return {
        "registrations": {item["sourceKey"]: _identity_key(item["ref"]) for item in bundle["registrations"]},
        "evidence": {_evidence_key(item, artifact_hashes): item["evidenceId"] for item in bundle["evidence"]},
        "facts": {fact_key_m1(item): item["factId"] for item in bundle["facts"]},
        "assessments": {_record_identity(item, "assessmentId"): item["assessmentId"]
                         for item in bundle["assessments"]},
        "coverage": {_record_identity(item, "coverageId"): item["coverageId"]
                     for item in bundle["coverage"]},
        "diagnostics": {_record_identity(item, "__none__"): _record_identity(item, "__none__")
                        for item in bundle["diagnostics"]}}


def _write_bundle(connection: sqlite3.Connection, result: dict, generation: int) -> None:
    session = result["session"]
    analysis_id = session["analysisId"]
    connection.execute("INSERT INTO sessions VALUES(?,?,?) ON CONFLICT(analysis_id) DO UPDATE SET session_json=excluded.session_json,generation=excluded.generation",
                       (analysis_id, _json(session), generation))
    for table in ("registrations", "evidence", "facts", "assessments", "coverage", "diagnostics", "artifacts"):
        connection.execute(f"DELETE FROM {table} WHERE analysis_id=?", (analysis_id,))
    bundle = result["bundle"]
    artifact_hashes = {item["artifactId"]: item["sha256"] for item in result["artifacts"]}
    for item in bundle["registrations"]:
        connection.execute("INSERT INTO registrations VALUES(?,?,?,?)",
            (analysis_id, item["sourceKey"], _identity_key(item["ref"]), _json(item)))
    for item in bundle["evidence"]:
        key = _evidence_key(item, artifact_hashes)
        connection.execute("INSERT INTO evidence VALUES(?,?,?,?)", (analysis_id, key, item["evidenceId"], _json(item)))
    for item in bundle["facts"]:
        connection.execute("INSERT INTO facts VALUES(?,?,?,?)", (analysis_id, fact_key_m1(item), item["factId"], _json(item)))
    for item in bundle["assessments"]:
        connection.execute("INSERT INTO assessments VALUES(?,?,?,?)",
            (analysis_id, _record_identity(item, "assessmentId"), item["assessmentId"], _json(item)))
    for item in bundle["coverage"]:
        connection.execute("INSERT INTO coverage VALUES(?,?,?,?)",
            (analysis_id, _record_identity(item, "coverageId"), item["coverageId"], _json(item)))
    for index, item in enumerate(bundle["diagnostics"]):
        connection.execute("INSERT INTO diagnostics VALUES(?,?,?)", (analysis_id, f"{index}:{_record_identity(item, '__none__')}", _json(item)))
    for item in result["artifacts"]:
        connection.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?)",
            (analysis_id, item["sha256"], item["artifactId"], item["mediaType"], item["content"], _json(item)))


def commit_m1(store: SemanticFactStore | Path | str, candidate: dict) -> dict:
    repository = store if isinstance(store, SemanticFactStore) else SemanticFactStore(store)
    operation_id, session, content_hash = _validate_candidate(candidate, repository)
    analysis_id = session["analysisId"]
    expected_generation = candidate["expectedGeneration"]
    try:
        with repository._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            prior_receipt = connection.execute(
                "SELECT content_hash,payload FROM receipts WHERE analysis_id=? AND operation_id=?",
                (analysis_id, operation_id)).fetchone()
            if prior_receipt:
                if prior_receipt[0] != content_hash:
                    raise ValueError("operation ID was already used with different content")
                connection.commit()
                return json.loads(prior_receipt[1])
            current = _read_connection(connection, analysis_id)
            current_generation = current["generation"]
            if current_generation != expected_generation:
                receipt = _receipt(operation_id, "failed", current_generation,
                    diagnostics=[{"code": "INPUT_MISMATCH", "message": "Stored generation changed before commit."}])
                connection.rollback()
                return receipt
            if current["session"] is not None:
                stable_fields = ("inputId", "root", "store", "identityDomain", "profile")
                if any(current["session"].get(key) != session.get(key) for key in stable_fields):
                    raise ValueError("M1 session input or identity domain changed")
                session = {**current["session"], **session,
                           "tools": sorted({tuple(sorted(item.items())) for item in
                               current["session"].get("tools", []) + session.get("tools", [])})}
                session["tools"] = [dict(item) for item in session["tools"]]
            result = canonicalize_m1(session, current, candidate["bundle"], candidate["artifacts"])
            validation = __import__("c2s_semantic_contract.validation", fromlist=["semantic_model_catalogs", "validate_model"])
            check = validation.validate_model(result["bundle"], validation.semantic_model_catalogs("m1-project-discovery-1"))
            if not check["valid"]:
                raise ValueError("canonical M1 bundle failed validation")
            old_keys = _record_keys(current["bundle"], current["artifacts"])
            new_keys = _record_keys(result["bundle"], result["artifacts"])
            changes = any(set(old_keys[name]) != set(new_keys[name]) for name in old_keys)
            artifact_change = {item["sha256"] for item in current["artifacts"]} != {
                item["sha256"] for item in result["artifacts"]}
            session_change = current["session"] != session
            state = "stored" if current["session"] is None or changes or artifact_change or session_change else "already_stored"
            generation = current_generation + 1 if state == "stored" else current_generation
            receipt = _receipt(operation_id, state, generation,
                added=[value for key, value in new_keys["facts"].items() if key not in old_keys["facts"]],
                existing=[value for key, value in new_keys["facts"].items() if key in old_keys["facts"]])
            _write_bundle(connection, result, generation)
            connection.execute("INSERT INTO receipts VALUES(?,?,?,?)",
                               (analysis_id, operation_id, content_hash, _json(receipt)))
            connection.commit()
            return receipt
    except sqlite3.Error as error:
        return _receipt(operation_id, "failed", expected_generation,
            diagnostics=[{"code": "STORE_WRITE_FAILED", "message": type(error).__name__}])


def lookup_m1(store: SemanticFactStore | Path | str, analysis_id: str,
              operation_id: str) -> dict:
    repository = store if isinstance(store, SemanticFactStore) else SemanticFactStore(store)
    with repository._connect() as connection:
        row = connection.execute("SELECT payload FROM receipts WHERE analysis_id=? AND operation_id=?",
                                 (analysis_id, operation_id)).fetchone()
    if row is None:
        return _receipt(operation_id, "unknown", 0,
            diagnostics=[{"code": "COMMIT_UNKNOWN", "message": "No stored receipt matches this operation."}])
    return json.loads(row[0])


def remember_query_report(store: SemanticFactStore | Path | str, root: Path | str,
                          selector: str, source_digest: str, profile_digest: str,
                          analysis_id: str, payload: dict) -> None:
    repository = store if isinstance(store, SemanticFactStore) else SemanticFactStore(store)
    resolved = str(Path(root).resolve(strict=True))
    repository.validate_root(resolved)
    with repository._connect() as connection:
        connection.execute("INSERT INTO semantic_query_reports VALUES(?,?,?,?,?,?) ON CONFLICT(root,selector,source_digest,profile_digest) DO UPDATE SET analysis_id=excluded.analysis_id,payload=excluded.payload",
            (resolved, selector, source_digest, profile_digest, analysis_id, _json(payload)))


def read_query_report(store: SemanticFactStore | Path | str, root: Path | str, selector: str,
                      source_digest: str, profile_digest: str) -> dict | None:
    repository = store if isinstance(store, SemanticFactStore) else SemanticFactStore(store)
    resolved = str(Path(root).resolve(strict=True))
    repository.validate_root(resolved)
    with repository._connect() as connection:
        row = connection.execute("SELECT analysis_id,payload FROM semantic_query_reports WHERE root=? AND selector=? AND source_digest=? AND profile_digest=?",
                                  (resolved, selector, source_digest, profile_digest)).fetchone()
    if row is None:
        return None
    return {"analysisId": row[0], "response": json.loads(row[1])}


def read_bundle(store: SemanticFactStore | Path | str, analysis_id: str) -> dict:
    """Read the canonical bundle for either supported profile."""
    repository = store if isinstance(store, SemanticFactStore) else SemanticFactStore(store)
    with repository._connect() as connection:
        row = connection.execute("SELECT payload FROM full_bundles WHERE analysis_id=?", (analysis_id,)).fetchone()
        normalized = connection.execute("SELECT collection, payload FROM semantic_records WHERE analysis_id=? ORDER BY collection,record_key",
                                         (analysis_id,)).fetchall()
        if normalized:
            result = _read_connection(connection, analysis_id)
            collections = {name: [] for name in _FULL_COLLECTIONS}
            for collection, payload in normalized:
                collections[collection].append(json.loads(payload))
            for records in collections.values():
                records.sort(key=_json)
            result["bundle"] = {"version": "1.0.0", "profile": "semantic-fact-model-1", **collections}
        elif row is not None:
            result = _read_connection(connection, analysis_id)
            result["bundle"] = json.loads(row[0])
        else:
            result = _read_connection(connection, analysis_id)
        observation_rows = connection.execute("SELECT payload FROM source_observations WHERE analysis_id=? ORDER BY evidence_id",
                                              (analysis_id,)).fetchall()
        result["sourceObservations"] = {"items": [json.loads(item[0]) for item in observation_rows]}
    if result["session"] is not None:
        repository.validate_root(result["session"]["root"])
    return result


def commit_bundle(store: SemanticFactStore | Path | str, candidate: dict) -> dict:
    """Atomically persist a validated full-profile bundle, retaining every model collection."""
    repository = store if isinstance(store, SemanticFactStore) else SemanticFactStore(store)
    session = candidate.get("session", {})
    if session.get("profile") != "semantic-fact-model-1":
        raise ValueError("full semantic bundle requires semantic-fact-model-1 session")
    required = {"analysisId", "inputId", "root", "store", "identityDomain", "profile", "host", "target", "tools"}
    if not required <= set(session):
        raise ValueError("session is missing required analysis identity fields")
    for field in ("analysisId", "inputId", "identityDomain"):
        UUID(session[field])
    root = Path(session["root"]).resolve(strict=True)
    repository.validate_root(root)
    if Path(session["store"]).resolve() != repository.path:
        raise ValueError("session store path does not match repository")
    operation_id, expected = candidate.get("operationId"), candidate.get("expectedGeneration")
    if not isinstance(operation_id, str) or not operation_id or type(expected) is not int or expected < 0:
        raise ValueError("commit requires operationId and expectedGeneration")
    bundle = canonicalize_semantic(candidate.get("bundle", {}))
    from c2s_semantic_contract.validation import semantic_model_catalogs, validate_model
    check = validate_model(bundle, semantic_model_catalogs(), candidate.get("sourceObservations"))
    if not check["valid"]:
        raise ValueError("full semantic bundle failed contract validation: " + ", ".join(
            item.get("ruleCode", "CONTRACT_INVALID") for item in check["diagnostics"]))
    artifacts = candidate.get("artifacts", [])
    for artifact in artifacts:
        if not isinstance(artifact.get("content"), str) or _sha(artifact["content"].encode()) != artifact.get("sha256"):
            raise ValueError("artifact content digest is invalid")
    content_hash = _sha(_json({"session": session, "bundle": bundle, "artifacts": artifacts}).encode())
    with repository._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        prior = connection.execute("SELECT content_hash,payload FROM receipts WHERE analysis_id=? AND operation_id=?",
                                   (session["analysisId"], operation_id)).fetchone()
        if prior:
            if prior[0] != content_hash:
                raise ValueError("operation ID was already used with different content")
            return json.loads(prior[1])
        current = _read_connection(connection, session["analysisId"])
        if current["generation"] != expected:
            connection.rollback()
            return _receipt(operation_id, "failed", current["generation"], diagnostics=[
                {"code": "INPUT_MISMATCH", "message": "Stored generation changed before commit."}])
        if current["session"] is not None and any(current["session"].get(k) != session.get(k)
                                                   for k in ("inputId", "root", "store", "identityDomain", "profile")):
            raise ValueError("session input or identity domain changed")
        generation = expected + 1
        connection.execute("INSERT INTO sessions VALUES(?,?,?) ON CONFLICT(analysis_id) DO UPDATE SET session_json=excluded.session_json,generation=excluded.generation",
                           (session["analysisId"], _json(session), generation))
        old_row = connection.execute("SELECT payload FROM full_bundles WHERE analysis_id=?",
                                     (session["analysisId"],)).fetchone()
        if old_row:
            bundle = _merge_semantic_bundles(json.loads(old_row[0]), bundle)
        connection.execute("INSERT INTO full_bundles VALUES(?,?) ON CONFLICT(analysis_id) DO UPDATE SET payload=excluded.payload",
                           (session["analysisId"], _json(bundle)))
        connection.execute("DELETE FROM semantic_records WHERE analysis_id=?", (session["analysisId"],))
        connection.execute("DELETE FROM semantic_refs WHERE analysis_id=?", (session["analysisId"],))
        for observation in candidate.get("sourceObservations", {}).get("items", []):
            connection.execute("INSERT INTO source_observations VALUES(?,?,?) ON CONFLICT(analysis_id,evidence_id) DO UPDATE SET payload=excluded.payload",
                (session["analysisId"], observation["evidenceId"], _json(observation)))
        for artifact in artifacts:
            connection.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?) ON CONFLICT(analysis_id,sha256) DO UPDATE SET artifact_id=excluded.artifact_id,media_type=excluded.media_type,content=excluded.content,payload=excluded.payload",
                (session["analysisId"], artifact["sha256"], artifact.get("artifactId", artifact["sha256"]),
                 artifact.get("mediaType", "application/json"), artifact["content"], _json(artifact)))
        id_fields = {"registrations": "sourceKey", "assessments": "assessmentId", "facts": "factId",
            "evidence": "evidenceId", "coverage": "coverageId", "dependencies": "dependencyId",
            "dependencyResolutions": "resolutionId", "semanticStates": "stateId",
            "diagnostics": None, "contextDomains": "keyId", "contexts": "contextId"}
        for collection in _FULL_COLLECTIONS:
            for record in bundle[collection]:
                record_id = record.get(id_fields[collection]) if id_fields[collection] else _sha(_json(record).encode())
                connection.execute("INSERT INTO semantic_records VALUES(?,?,?,?)",
                    (session["analysisId"], collection, str(record_id), _json(record)))
                for field, target_collection, target_id in _semantic_references(collection, record):
                    connection.execute("INSERT OR IGNORE INTO semantic_refs VALUES(?,?,?,?,?,?)",
                        (session["analysisId"], collection, str(record_id), field, target_collection, str(target_id)))
        receipt = _receipt(operation_id, "stored", generation,
                           added=[item["factId"] for item in bundle["facts"]])
        connection.execute("INSERT INTO receipts VALUES(?,?,?,?)",
                           (session["analysisId"], operation_id, content_hash, _json(receipt)))
        connection.commit()
    return receipt


def query_bundle(store: SemanticFactStore | Path | str, analysis_id: str, selector: str) -> dict:
    """Return stored claims and selector coverage for a selector, without reconstructing facts."""
    result = read_bundle(store, analysis_id)
    bundle = result["bundle"]
    matching = [item for item in bundle.get("coverage", []) if item.get("selector") == selector]
    if not matching:
        return {"version": bundle["version"], "profile": bundle["profile"],
                **{name: [] for name in _FULL_COLLECTIONS}}
    states = [item for item in bundle.get("semanticStates", []) if item.get("selector") == selector]
    fact_ids = {fact_id for item in states for fact_id in item.get("factIds", [])}
    facts = [item for item in bundle["facts"] if item["factId"] in fact_ids]
    evidence_ids = {value for item in facts for value in item.get("evidenceIds", [])}
    evidence_ids.update(value for item in matching + states for value in item.get("evidenceIds", []))
    identities = set()
    def collect_refs(value):
        if isinstance(value, dict):
            identity = value.get("identity")
            if isinstance(identity, dict) and {"authority", "domainId", "localId"} <= set(identity):
                identities.add(_json({key: identity[key] for key in ("authority", "domainId", "localId")}))
            for child in value.values():
                collect_refs(child)
        elif isinstance(value, list):
            for child in value:
                collect_refs(child)
    for fact in facts:
        collect_refs(fact)
    dependencies = [item for item in bundle.get("dependencies", [])
                    if _json(item.get("consumer", {}).get("identity", {})) in identities]
    dependency_ids = {item["dependencyId"] for item in dependencies}
    resolutions = [item for item in bundle.get("dependencyResolutions", [])
                   if item.get("dependencyId") in dependency_ids]
    registrations = [item for item in bundle.get("registrations", [])
                     if _identity_key(item["ref"]) in identities]
    for item in registrations:
        evidence_ids.update(item.get("evidenceIds", []))
    evidence = [item for item in bundle.get("evidence", []) if item["evidenceId"] in evidence_ids]
    context_ids = {item["contextRef"] for item in facts if item.get("contextRef")}
    contexts = [item for item in bundle.get("contexts", []) if item.get("contextId") in context_ids]
    domain_keys = {key for item in contexts for key in item.get("assignments", {})}
    result = {name: [] for name in _FULL_COLLECTIONS}
    result.update(version=bundle["version"], profile=bundle["profile"], facts=facts,
                  coverage=matching, semanticStates=states, registrations=registrations,
                  evidence=evidence, dependencies=dependencies, dependencyResolutions=resolutions,
                  contexts=contexts, contextDomains=[item for item in bundle.get("contextDomains", [])
                                                     if item.get("keyId") in domain_keys],
                  assessments=[item for item in bundle.get("assessments", [])
                               if item.get("recordId") in fact_ids or item.get("factId") in fact_ids],
                  diagnostics=[item for item in bundle.get("diagnostics", [])
                               if item.get("recordId") in fact_ids or item.get("recordId") in
                               {row["coverageId"] for row in matching}])
    return result
