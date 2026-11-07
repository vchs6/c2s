"""M1 semantic-fact repository with canonical identities and atomic SQLite commits."""

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
