"""M1 structural and identity validation; this module never executes project tools."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator


_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _ROOT / "contracts" / "semantic-model" / "fact.schema.json"
_SUPPORTED_KINDS = {"Project", "PackageSpecification", "NativeWorkspace", "SourceDeclaration"}


def _diagnostic(stage: str, rule_code: str, message: str, *, record_ref: str | None = None,
                field_path: str = "", severity: str = "error", related_refs: list[str] | None = None) -> dict:
    return {"stage": stage, "recordRef": record_ref, "fieldPath": field_path,
            "ruleCode": rule_code, "severity": severity, "relatedRefs": related_refs or [], "message": message}


def _identity_key(ref: dict) -> tuple[str, str, str]:
    identity = ref["identity"]
    return identity["authority"], identity["domainId"], identity["localId"]


def register_m1(domain_id: str, registrations: list[dict], kind: str,
                source_key: str, evidence_ids: list[str]) -> dict:
    """Return the stable registration for a source key, merging evidence monotonically."""
    if not isinstance(domain_id, str) or not domain_id.strip() \
            or not isinstance(registrations, list) or any(not isinstance(item, dict) for item in registrations) \
            or not isinstance(kind, str) or kind not in _SUPPORTED_KINDS \
            or not isinstance(source_key, str) or not source_key.strip() \
            or not isinstance(evidence_ids, list) or not evidence_ids \
            or any(not isinstance(item, str) or not item.strip() for item in evidence_ids):
        return {"code": "CONTRACT_INVALID", "severity": "error", "recordId": None,
                "path": None, "message": "M1 registration requires non-empty domain, supported kind, source key and evidence IDs."}
    for item in registrations:
        ref = item.get("ref")
        identity = ref.get("identity") if isinstance(ref, dict) else None
        if (not isinstance(ref, dict) or ref.get("kind") not in _SUPPORTED_KINDS
                or not isinstance(identity, dict)
                or any(not isinstance(identity.get(key), str) or not identity[key].strip()
                       for key in ("authority", "domainId", "localId"))
                or not isinstance(item.get("sourceKey"), str) or not item["sourceKey"].strip()
                or not isinstance(item.get("evidenceIds"), list) or not item["evidenceIds"]
                or any(not isinstance(value, str) or not value.strip() for value in item["evidenceIds"])):
            return {"code": "CONTRACT_INVALID", "severity": "error", "recordId": None,
                    "path": None, "message": "Existing M1 registrations must satisfy the public registration shape."}
    matches = [item for item in registrations if item.get("sourceKey") == source_key]
    if matches:
        existing = matches[0]
        if len(matches) != 1 or existing.get("ref", {}).get("kind") != kind:
            identity = existing.get("ref", {}).get("identity", {})
            return {"code": "CONTRACT_INVALID", "severity": "error", "recordId": identity.get("localId"),
                    "path": None, "message": "sourceKey is already registered with a different kind or duplicate registration."}
        identity = existing.get("ref", {}).get("identity", {})
        if identity.get("domainId") != domain_id:
            return {"code": "CONTRACT_INVALID", "severity": "error", "recordId": identity.get("localId"),
                    "path": None, "message": "sourceKey registration belongs to a different identity domain."}
        return {"ref": deepcopy(existing["ref"]), "sourceKey": source_key,
                "evidenceIds": sorted(set(existing["evidenceIds"]) | set(evidence_ids))}
    return {"ref": {"identity": {"authority": "c2s-local", "domainId": domain_id,
                                   "localId": str(uuid4())}, "kind": kind},
            "sourceKey": source_key, "evidenceIds": sorted(set(evidence_ids))}


def validate_model(document: dict, catalogs: dict, source_observations: dict | None = None) -> dict:
    """Validate the M1 wire shape and local references without claiming source truth."""
    del catalogs, source_observations  # catalog and evidence observation checks are added by their owning slices.
    result = {"valid": False,
              "stages": {"catalog": "partial", "structure": "not_run", "references": "not_run", "invariants": "not_run"},
              "diagnostics": [], "consistency": "undetermined"}
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    if errors:
        result["stages"]["structure"] = "fail"
        result["diagnostics"] = [_diagnostic("structure", "CONTRACT_INVALID", error.message,
            field_path="/" + "/".join(map(str, error.absolute_path))) for error in errors]
        return result
    result["stages"]["structure"] = "pass"

    registrations = document["registrations"]
    identity_kinds: dict[tuple[str, str, str], tuple[str, str]] = {}
    sources: dict[str, dict] = {}
    diagnostics = []
    for index, registration in enumerate(registrations):
        ref = registration["ref"]
        identity = _identity_key(ref)
        previous = identity_kinds.get(identity)
        if previous and previous[0] != ref["kind"]:
            diagnostics.append(_diagnostic("references", "IDENTITY_KIND_CONFLICT",
                "One identity is registered with incompatible subject kinds.", record_ref=f"registration:{index}",
                field_path=f"/registrations/{index}/ref/kind", related_refs=[previous[1]]))
        identity_kinds[identity] = (ref["kind"], f"registration:{index}")
        source_key = registration["sourceKey"]
        if source_key in sources:
            previous_ref = sources[source_key]["ref"]
            rule = ("SOURCE_KEY_IDENTITY_CONFLICT" if _identity_key(previous_ref) != identity
                    else "SOURCE_KEY_DUPLICATE")
            diagnostics.append(_diagnostic("references", rule,
                "A sourceKey must map to exactly one registration record.", record_ref=f"registration:{index}",
                field_path=f"/registrations/{index}/sourceKey",
                related_refs=[f"registration:{source_key}"]))
        else:
            sources[source_key] = registration
    registered = {_identity_key(item["ref"]): item["ref"]["kind"] for item in registrations}
    evidence_ids = {item["evidenceId"] for item in document["evidence"]}

    def check_ref(ref: dict, field_path: str, record_ref: str) -> None:
        key = _identity_key(ref)
        if key not in registered:
            diagnostics.append(_diagnostic("references", "INTERNAL_REF_MISSING",
                "Internal subject reference does not resolve to a registration.", record_ref=record_ref,
                field_path=field_path))
        elif registered[key] != ref["kind"]:
            diagnostics.append(_diagnostic("references", "IDENTITY_KIND_CONFLICT",
                "Subject reference kind does not match its registered identity.", record_ref=record_ref,
                field_path=field_path))

    def check_evidence(refs: list[str], field_path: str, record_ref: str) -> None:
        for evidence_id in refs:
            if evidence_id not in evidence_ids:
                diagnostics.append(_diagnostic("references", "EVIDENCE_REF_MISSING",
                    "Evidence reference does not resolve to an evidence record.", record_ref=record_ref,
                    field_path=field_path))

    for index, fact in enumerate(document["facts"]):
        record_ref = f"fact:{fact['factId']}"
        check_ref(fact["subject"], f"/facts/{index}/subject", record_ref)
        if isinstance(fact["value"], dict):
            check_ref(fact["value"], f"/facts/{index}/value", record_ref)
        check_evidence(fact["evidenceIds"], f"/facts/{index}/evidenceIds", record_ref)
    for index, registration in enumerate(registrations):
        check_evidence(registration["evidenceIds"], f"/registrations/{index}/evidenceIds",
                       f"registration:{index}")
    for index, assessment in enumerate(document["assessments"]):
        record_ref = f"assessment:{assessment['assessmentId']}"
        check_ref(assessment["declaration"], f"/assessments/{index}/declaration", record_ref)
        for project_index, project in enumerate(assessment["projects"]):
            check_ref(project, f"/assessments/{index}/projects/{project_index}", record_ref)
        check_evidence(assessment["evidenceIds"], f"/assessments/{index}/evidenceIds", record_ref)
    for index, coverage in enumerate(document["coverage"]):
        if coverage["subject"] is not None:
            check_ref(coverage["subject"], f"/coverage/{index}/subject", f"coverage:{coverage['coverageId']}")
        check_evidence(coverage["evidenceIds"], f"/coverage/{index}/evidenceIds", f"coverage:{coverage['coverageId']}")
    if diagnostics:
        result["stages"]["references"] = "fail"
        result["diagnostics"] = diagnostics
        return result
    result["stages"]["references"] = "pass"
    invariant_diagnostics = []
    for index, evidence in enumerate(document["evidence"]):
        if evidence["endByte"] < evidence["startByte"]:
            invariant_diagnostics.append(_diagnostic("invariants", "BYTE_RANGE_INVALID",
                "Evidence endByte must be greater than or equal to startByte.",
                record_ref=f"evidence:{evidence['evidenceId']}",
                field_path=f"/evidence/{index}/endByte"))

    for collection_name, id_field, prefix in (
        ("facts", "factId", "fact"), ("assessments", "assessmentId", "assessment"),
        ("coverage", "coverageId", "coverage"), ("evidence", "evidenceId", "evidence"),
    ):
        seen_ids = {}
        for index, record in enumerate(document[collection_name]):
            record_id = record[id_field]
            if record_id in seen_ids:
                invariant_diagnostics.append(_diagnostic("invariants", "DUPLICATE_RECORD_ID",
                    "Record IDs must be unique within an M1 bundle.", record_ref=f"{prefix}:{record_id}",
                    field_path=f"/{collection_name}/{index}/{id_field}", related_refs=[seen_ids[record_id]]))
            else:
                seen_ids[record_id] = f"{prefix}:{record_id}"

    if invariant_diagnostics:
        result["stages"]["invariants"] = "fail"
        result["diagnostics"] = invariant_diagnostics
        return result
    result["stages"]["invariants"] = "partial"
    result["valid"] = True
    result["consistency"] = "undetermined"
    return result
