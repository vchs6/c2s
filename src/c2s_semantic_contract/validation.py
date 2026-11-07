"""M1 structural and identity validation; this module never executes project tools."""

from __future__ import annotations

import json
from copy import deepcopy
import hashlib
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from .conditions import classify_claim_overlap, condition_satisfiability, diagnose_conditional_cycles


_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _ROOT / "contracts" / "semantic-model" / "fact.schema.json"
_CATALOG_SCHEMA_PATH = _ROOT / "contracts" / "semantic-model" / "catalog.schema.json"
_TYPES_PATH = _ROOT / "contracts" / "semantic-model" / "types.json"
_PREDICATES_PATH = _ROOT / "contracts" / "semantic-model" / "predicates.json"
_CATALOG_MANIFEST_PATH = _ROOT / "contracts" / "semantic-model" / "catalog-manifest.json"
_SEMANTIC_TYPES_PATH = _ROOT / "contracts" / "semantic-model" / "semantic-types.json"
_SEMANTIC_PREDICATES_PATH = _ROOT / "contracts" / "semantic-model" / "semantic-predicates.json"
_SEMANTIC_CATALOG_MANIFEST_PATH = _ROOT / "contracts" / "semantic-model" / "semantic-catalog-manifest.json"
_TRUSTED_MANIFEST_SHA256 = "34e533b34af5fdb135e2fd8cea22de95a964b702b714619f314a30bd4cd49c2b"
_TRUSTED_SEMANTIC_MANIFEST_SHA256 = "35c99a715a99e78dbe43290fcbcc342d655241f35f3724d311c7765d4b66c659"
_M1_SUPPORTED_KINDS = {"Project", "PackageSpecification", "NativeWorkspace", "SourceDeclaration"}
_SUPPORTED_KINDS = _M1_SUPPORTED_KINDS | {"BehaviorBody", "BehaviorRegion", "BehaviorStep",
    "BuildTarget", "BuildRecipe", "BuildAlias", "OutputSpecification", "ArtifactObservation",
    "Binding", "AlgorithmDescription", "PseudocodeView", "Signature", "AccessConstraint",
    "CoordinationGroup", "UsageRequirement", "EntryPoint", "BuildTask", "DependencyRequirement",
    "DependencyProvider"}
_SUPPORTED_CONSTRAINTS = {
    "KIND_MATCH", "ROLE_CARDINALITY", "INTERNAL_REF_EXISTS", "DOMAIN_UNIQUE",
    "CONTEXT_KEYS_SINGLE_VALUED", "PROJECT_MAPPING_CARDINALITY", "LAYER_CLASSIFICATION",
    "INLINE_WHITELIST", "STATE_COMBINATION", "CLOSED_NEGATIVE_BASIS", "ALGORITHM_STEP_REFS",
    "CONDITION_SUPPORTED_FRAGMENT",
}


def _diagnostic(stage: str, rule_code: str, message: str, *, record_ref: str | None = None,
                field_path: str = "", severity: str = "error", related_refs: list[str] | None = None) -> dict:
    return {"stage": stage, "recordRef": record_ref, "fieldPath": field_path,
            "ruleCode": rule_code, "severity": severity, "relatedRefs": related_refs or [], "message": message}


def _identity_key(ref: dict) -> tuple[str, str, str]:
    identity = ref["identity"]
    return identity["authority"], identity["domainId"], identity["localId"]


def _canonical_digest(value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _diagnostic_key(diagnostic: dict) -> str:
    return json.dumps([diagnostic["code"], diagnostic["recordId"], diagnostic["path"]],
                      ensure_ascii=False, separators=(",", ":"))


def _manifest_integrity(manifest: dict, profile: str = "m1-project-discovery-1") -> bool:
    expected = (_TRUSTED_MANIFEST_SHA256 if profile == "m1-project-discovery-1"
                else _TRUSTED_SEMANTIC_MANIFEST_SHA256)
    return bool(expected) and isinstance(manifest, dict) and _canonical_digest(manifest) == expected


def semantic_model_catalogs(profile: str = "semantic-fact-model-1") -> dict:
    """Load pinned catalogs for the requested supported semantic bundle profile."""
    if profile == "m1-project-discovery-1":
        types_path, predicates_path = _TYPES_PATH, _PREDICATES_PATH
    elif profile == "semantic-fact-model-1":
        types_path, predicates_path = _SEMANTIC_TYPES_PATH, _SEMANTIC_PREDICATES_PATH
    else:
        raise ValueError(f"unsupported semantic catalog profile: {profile}")
    return {"types": json.loads(types_path.read_text(encoding="utf-8")),
            "predicates": json.loads(predicates_path.read_text(encoding="utf-8"))}


def _validate_catalogs(catalogs: dict, document_profile: str = "m1-project-discovery-1") -> list[dict]:
    diagnostics = []
    if not isinstance(catalogs, dict) or set(catalogs) != {"types", "predicates"}:
        return [_diagnostic("catalog", "CATALOG_BUNDLE_MISMATCH",
            "Callers must supply exactly the bundled types and predicates records.", field_path="/catalogs")]
    catalog_profile = catalogs.get("predicates", {}).get("profile") if isinstance(catalogs, dict) else None
    if (document_profile == "m1-project-discovery-1" and catalog_profile != "m1-project-discovery-1"
            or document_profile == "semantic-fact-model-1" and catalog_profile not in
            {"m1-project-discovery-1", "semantic-fact-model-1"}):
        return [_diagnostic("catalog", "CATALOG_PROFILE_MISMATCH",
            "Catalog profile is not compatible with the semantic fact bundle profile.", field_path="/catalogs/profile")]
    full_catalog = catalog_profile == "semantic-fact-model-1"
    types_path = _SEMANTIC_TYPES_PATH if full_catalog else _TYPES_PATH
    predicates_path = _SEMANTIC_PREDICATES_PATH if full_catalog else _PREDICATES_PATH
    manifest_path = _SEMANTIC_CATALOG_MANIFEST_PATH if full_catalog else _CATALOG_MANIFEST_PATH
    try:
        expected_types = json.loads(types_path.read_text(encoding="utf-8"))
        expected_predicates = json.loads(predicates_path.read_text(encoding="utf-8"))
        catalog_schema = json.loads(_CATALOG_SCHEMA_PATH.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [_diagnostic("catalog", "CATALOG_INVALID", f"Bundled catalog files cannot be read: {type(error).__name__}.")]

    if not _manifest_integrity(manifest, catalog_profile):
        return [_diagnostic("catalog", "CATALOG_BUNDLE_MISMATCH",
            "The trusted catalog manifest digest does not match this validator release.", field_path="/catalog-manifest")]
    try:
        Draft202012Validator.check_schema(catalog_schema)
    except SchemaError as error:
        return [_diagnostic("catalog", "CATALOG_INVALID",
            f"Bundled catalog schema is invalid: {type(error).__name()}.", field_path="/catalog.schema.json")]
    bundled = {"version": "1.0.0", "profile": catalog_profile,
               "types": catalogs["types"], "predicates": catalogs["predicates"]}
    errors = sorted(Draft202012Validator(catalog_schema).iter_errors(bundled),
                    key=lambda error: list(error.absolute_path))
    if errors:
        return [_diagnostic("catalog", "CATALOG_INVALID", error.message,
                            field_path="/catalogs/" + "/".join(map(str, error.absolute_path)))
                for error in errors]

    types_by_id = {item["typeId"] for item in catalogs["types"]["types"]}
    enum_ids = set(catalogs["types"]["enums"])
    for type_index, type_record in enumerate(catalogs["types"]["types"]):
        for field_name, field_record in type_record["fields"].items():
            ref = field_record["type"]
            if ref not in types_by_id | enum_ids | {"Id", "Id[]", "string", "bool", "int", "Path"}:
                diagnostics.append(_diagnostic("catalog", "CATALOG_TYPE_REF_MISSING",
                    f"Type field references unknown type {ref}.", field_path=f"/catalogs/types/types/{type_index}/fields/{field_name}/type"))

    predicate_ids = set()
    for index, predicate in enumerate(catalogs["predicates"]["predicates"]):
        predicate_id = predicate["predicateId"]
        if predicate_id in predicate_ids:
            diagnostics.append(_diagnostic("catalog", "PREDICATE_ID_DUPLICATE",
                "Predicate IDs must be unique.", field_path=f"/catalogs/predicates/predicates/{index}/predicateId"))
        predicate_ids.add(predicate_id)
        if predicate["category"] == "Semantic" and predicate["primaryLayer"] is None:
            diagnostics.append(_diagnostic("catalog", "LAYER_CLASSIFICATION",
                "Semantic predicates require exactly one primary layer.", field_path=f"/catalogs/predicates/predicates/{index}/primaryLayer"))
        if predicate["category"] == "Provenance" and predicate["primaryLayer"] is not None:
            diagnostics.append(_diagnostic("catalog", "LAYER_CLASSIFICATION",
                "Provenance predicates must not declare a primary layer.", field_path=f"/catalogs/predicates/predicates/{index}/primaryLayer"))
        role_ids = [role["roleId"] for role in predicate["roles"]]
        positions = [role["position"] for role in predicate["roles"]]
        binary_positions = positions == ["subject", "value"] or positions == ["value", "subject"]
        nary_positions = (full_catalog and positions.count("subject") == 1 and "value" not in positions
                          and positions.count("argument") >= 2)
        if len(set(role_ids)) != len(role_ids) or not (binary_positions or nary_positions):
            diagnostics.append(_diagnostic("catalog", "ROLE_CARDINALITY",
                "Predicate roles must declare either one subject/value pair or one subject and multiple full-profile arguments.",
                field_path=f"/catalogs/predicates/predicates/{index}/roles"))
        for role_index, role in enumerate(predicate["roles"]):
            if role["valueType"] not in types_by_id | enum_ids | {"string", "bool", "int", "Path"}:
                diagnostics.append(_diagnostic("catalog", "CATALOG_TYPE_REF_MISSING",
                    f"Role references unknown type {role['valueType']}.",
                    field_path=f"/catalogs/predicates/predicates/{index}/roles/{role_index}/valueType"))
            enum_values = set().union(*catalogs["types"]["enums"].values())
            for kind in role["allowedKinds"]:
                if kind not in enum_values:
                    diagnostics.append(_diagnostic("catalog", "CATALOG_KIND_REF_MISSING",
                        f"Role references unknown subject kind {kind}.",
                        field_path=f"/catalogs/predicates/predicates/{index}/roles/{role_index}/allowedKinds"))
        for rule_index, rule_id in enumerate(predicate["constraints"]):
            if rule_id not in _SUPPORTED_CONSTRAINTS:
                diagnostics.append(_diagnostic("catalog", "RULE_UNSUPPORTED",
                    f"Constraint {rule_id} is not implemented by this contract version.",
                    field_path=f"/catalogs/predicates/predicates/{index}/constraints/{rule_index}"))
    if diagnostics:
        return diagnostics

    expected_files = ({"semantic-types.json": expected_types, "semantic-predicates.json": expected_predicates,
                       "catalog.schema.json": catalog_schema} if full_catalog else
                      {"types.json": expected_types, "predicates.json": expected_predicates,
                       "catalog.schema.json": catalog_schema})
    expected_digests = {name: _canonical_digest(value) for name, value in expected_files.items()}
    if manifest.get("version") != "1.0.0" or manifest.get("profile") != catalog_profile \
            or manifest.get("ruleSetId") != "semantic-model-1.0.0" \
            or manifest.get("digests") != expected_digests:
        return [_diagnostic("catalog", "CATALOG_BUNDLE_MISMATCH",
            "The trusted catalog manifest does not match the bundled type, predicate, and schema files.", field_path="/catalog-manifest")]
    type_key, predicate_key = (("semantic-types.json", "semantic-predicates.json") if full_catalog
                               else ("types.json", "predicates.json"))
    if (_canonical_digest(catalogs["types"]) != expected_digests[type_key]
            or _canonical_digest(catalogs["predicates"]) != expected_digests[predicate_key]):
        return [_diagnostic("catalog", "CATALOG_BUNDLE_MISMATCH",
            "Caller-supplied catalogs differ from the fixed 1.0.0 bundle.", field_path="/catalogs")]
    return []


def register_m1(domain_id: str, registrations: list[dict], kind: str,
                source_key: str, evidence_ids: list[str]) -> dict:
    """Return the stable registration for a source key, merging evidence monotonically."""
    if not isinstance(domain_id, str) or not domain_id.strip() \
            or not isinstance(registrations, list) or any(not isinstance(item, dict) for item in registrations) \
            or not isinstance(kind, str) or kind not in _M1_SUPPORTED_KINDS \
            or not isinstance(source_key, str) or not source_key.strip() \
            or not isinstance(evidence_ids, list) or not evidence_ids \
            or any(not isinstance(item, str) or not item.strip() for item in evidence_ids):
        return {"code": "CONTRACT_INVALID", "severity": "error", "recordId": None,
                "path": None, "message": "M1 registration requires non-empty domain, supported kind, source key and evidence IDs."}
    for item in registrations:
        ref = item.get("ref")
        identity = ref.get("identity") if isinstance(ref, dict) else None
        if (not isinstance(ref, dict) or ref.get("kind") not in _M1_SUPPORTED_KINDS
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
    result = {"valid": False,
              "stages": {"catalog": "not_run", "structure": "not_run", "references": "not_run", "invariants": "not_run"},
              "diagnostics": [], "consistency": "undetermined", "dependencyCycles": []}
    document_profile = document.get("profile") if isinstance(document, dict) else "m1-project-discovery-1"
    catalog_errors = _validate_catalogs(catalogs, document_profile)
    if catalog_errors:
        result["stages"]["catalog"] = "fail"
        result["diagnostics"] = catalog_errors
        return result
    result["stages"]["catalog"] = "pass"
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
    context_ids = {item["contextId"] for item in document.get("contexts", [])}
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

    if document["profile"] == "m1-project-discovery-1":
        def semantic_refs(value):
            if isinstance(value, dict):
                if isinstance(value.get("identity"), dict) and "kind" in value:
                    yield value
                for child in value.values():
                    yield from semantic_refs(child)
            elif isinstance(value, list):
                for child in value:
                    yield from semantic_refs(child)

        unsupported = [ref for ref in semantic_refs(document)
                       if ref.get("kind") not in _M1_SUPPORTED_KINDS]
        if unsupported:
            result["stages"]["references"] = "fail"
            result["diagnostics"] = [_diagnostic("references", "M1_KIND_UNSUPPORTED",
                "The M1 profile does not permit full semantic subject kinds.", field_path="/profile")]
            return result

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
        context_ref = ref.get("contextRef")
        if context_ref is not None and context_ref not in context_ids:
            diagnostics.append(_diagnostic("references", "CONTEXT_REF_MISSING",
                "Subject reference context does not resolve to a context record.", record_ref=record_ref,
                field_path=f"{field_path}/contextRef"))

    def check_evidence(refs: list[str], field_path: str, record_ref: str) -> None:
        for evidence_id in refs:
            if evidence_id not in evidence_ids:
                diagnostics.append(_diagnostic("references", "EVIDENCE_REF_MISSING",
                    "Evidence reference does not resolve to an evidence record.", record_ref=record_ref,
                    field_path=field_path))

    fact_ids = {item["factId"] for item in document["facts"]}
    for index, fact in enumerate(document["facts"]):
        record_ref = f"fact:{fact['factId']}"
        check_ref(fact["subject"], f"/facts/{index}/subject", record_ref)
        if isinstance(fact["value"], dict):
            check_ref(fact["value"], f"/facts/{index}/value", record_ref)
        for argument_index, argument in enumerate(fact.get("arguments", [])):
            if isinstance(argument["value"], dict):
                check_ref(argument["value"], f"/facts/{index}/arguments/{argument_index}/value", record_ref)
        check_evidence(fact["evidenceIds"], f"/facts/{index}/evidenceIds", record_ref)
        for evidence_ref_index, evidence_ref in enumerate(fact.get("evidenceRefs", [])):
            check_evidence([evidence_ref["evidenceId"]],
                           f"/facts/{index}/evidenceRefs/{evidence_ref_index}/evidenceId", record_ref)
        derivation = fact.get("derivation")
        if derivation is not None:
            for premise_index, premise_id in enumerate(derivation["premiseFactIds"]):
                if premise_id not in fact_ids:
                    diagnostics.append(_diagnostic("references", "DERIVATION_PREMISE_MISSING",
                        "Derivation premise does not resolve to a fact in the bundle.", record_ref=record_ref,
                        field_path=f"/facts/{index}/derivation/premiseFactIds/{premise_index}"))
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
        check_evidence(coverage["evidenceIds"], f"/coverage/{index}/evidenceIds",
                       f"coverage:{coverage['coverageId']}")
    for index, coverage in enumerate(document["coverage"]):
        if coverage["subject"] is not None:
            check_ref(coverage["subject"], f"/coverage/{index}/subject", f"coverage:{coverage['coverageId']}")
        check_evidence(coverage["evidenceIds"], f"/coverage/{index}/evidenceIds", f"coverage:{coverage['coverageId']}")
    for index, dependency in enumerate(document.get("dependencies", [])):
        record_ref = f"dependency:{dependency['dependencyId']}"
        check_ref(dependency["consumer"], f"/dependencies/{index}/consumer", record_ref)
        check_evidence(dependency["evidenceIds"], f"/dependencies/{index}/evidenceIds", record_ref)
    dependency_ids = {item["dependencyId"] for item in document.get("dependencies", [])}
    for index, resolution in enumerate(document.get("dependencyResolutions", [])):
        record_ref = f"dependencyResolution:{resolution['resolutionId']}"
        if resolution["dependencyId"] not in dependency_ids:
            diagnostics.append(_diagnostic("references", "DEPENDENCY_REF_MISSING",
                "Dependency resolution does not refer to a declared requirement.", record_ref=record_ref,
                field_path=f"/dependencyResolutions/{index}/dependencyId"))
        for provider_index, provider in enumerate(resolution["providers"]):
            check_ref(provider, f"/dependencyResolutions/{index}/providers/{provider_index}", record_ref)
        check_evidence(resolution["evidenceIds"], f"/dependencyResolutions/{index}/evidenceIds", record_ref)
    for index, state in enumerate(document.get("semanticStates", [])):
        record_ref = f"semanticState:{state['stateId']}"
        if state["subject"] is not None:
            check_ref(state["subject"], f"/semanticStates/{index}/subject", record_ref)
        check_evidence(state["evidenceIds"], f"/semanticStates/{index}/evidenceIds", record_ref)
        for fact_id in state["factIds"]:
            if fact_id not in fact_ids:
                diagnostics.append(_diagnostic("references", "STATE_FACT_REF_MISSING",
                    "Semantic state refers to a fact that is not in the bundle.", record_ref=record_ref,
                    field_path=f"/semanticStates/{index}/factIds"))
    if diagnostics:
        result["stages"]["references"] = "fail"
        result["diagnostics"] = diagnostics
        return result
    result["stages"]["references"] = "pass"
    requirements = {item["dependencyId"]: item for item in document.get("dependencies", [])}
    context_domains_for_graph = {item["keyId"]: item["values"] for item in document.get("contextDomains", [])}
    contexts_for_graph = {item["contextId"]: item for item in document.get("contexts", [])}
    graphs_by_configuration: dict[str | None, list[dict]] = {}
    for resolution in document.get("dependencyResolutions", []):
        if resolution["status"] == "unresolved":
            continue
        requirement = requirements.get(resolution["dependencyId"])
        if requirement is None:
            continue
        condition_parts = [requirement["condition"]]
        context_ref = requirement["consumer"].get("contextRef")
        if context_ref in contexts_for_graph:
            condition_parts.extend({"kind": "eq", "key": key_id, "value": value}
                                   for key_id, value in contexts_for_graph[context_ref]["assignments"].items())
        condition = {"kind": "all", "conditions": condition_parts}
        configuration = resolution["configuration"]
        graph_edges = graphs_by_configuration.setdefault(configuration, [])
        for provider_index, provider in enumerate(resolution["providers"]):
            graph_edges.append({"edgeId": f"{resolution['resolutionId']}:{provider_index}",
                                "source": json.dumps(_identity_key(requirement["consumer"]), ensure_ascii=False),
                                "target": json.dumps(_identity_key(provider), ensure_ascii=False), "condition": condition})
    result["dependencyCycles"] = [
        {"configuration": configuration, **diagnose_conditional_cycles(edges, context_domains_for_graph)}
        for configuration, edges in sorted(graphs_by_configuration.items(), key=lambda item: item[0] or "")]
    invariant_diagnostics = []
    context_domains = {item["keyId"]: item["values"] for item in document.get("contextDomains", [])}
    is_m1 = document.get("profile") == "m1-project-discovery-1"
    if is_m1 and (document.get("contextDomains") or document.get("contexts") or document.get("dependencies")
                  or document.get("dependencyResolutions") or any(
            fact.get("condition") != {"kind": "true"} for fact in document.get("facts", []))):
        invariant_diagnostics.append(_diagnostic("invariants", "M1_CONTEXT_UNSUPPORTED",
            "The M1 project-discovery profile does not permit context, conditional facts, or dependency records.",
            field_path="/profile"))
    if is_m1 and document.get("semanticStates"):
        invariant_diagnostics.append(_diagnostic("invariants", "M1_STATE_MODEL_UNSUPPORTED",
            "The M1 project-discovery profile does not support full semantic acquisition/presentation states.",
            field_path="/semanticStates"))
    if is_m1 and any(fact.get("claimMode") not in {"declaration", "interpretation"}
                     or fact.get("evidenceRefs") or fact.get("derivation") is not None
                     or fact.get("sourceMetadata") is not None
                     for fact in document.get("facts", [])):
        invariant_diagnostics.append(_diagnostic("invariants", "M1_MODALITY_UNSUPPORTED",
            "The M1 project-discovery profile supports declaration/interpretation claims without derivation links.",
            field_path="/facts"))
    if is_m1 and any(fact.get("polarity", "positive") != "positive" or fact.get("negativeBasis") is not None
                     for fact in document.get("facts", [])):
        invariant_diagnostics.append(_diagnostic("invariants", "M1_NEGATION_UNSUPPORTED",
            "The M1 project-discovery profile does not support negative claims.", field_path="/facts"))
    seen_context_ids = set()
    for context_index, context in enumerate(document.get("contexts", [])):
        context_id = context["contextId"]
        if context_id in seen_context_ids:
            invariant_diagnostics.append(_diagnostic("invariants", "CONTEXT_ID_DUPLICATE",
                "Context IDs must be unique.", record_ref=f"context:{context_id}",
                field_path=f"/contexts/{context_index}/contextId"))
        seen_context_ids.add(context_id)
    for key_id, values in context_domains.items():
        if (not values or any(type(value) not in {str, bool} for value in values)
                or len({type(value) for value in values}) != 1):
            invariant_diagnostics.append(_diagnostic("invariants", "CONTEXT_DOMAIN_INVALID",
                "A context domain must contain one or more unique values of one scalar type.",
                field_path=f"/contextDomains/{key_id}/values"))
    if len(context_domains) != len(document.get("contextDomains", [])):
        invariant_diagnostics.append(_diagnostic("invariants", "CONTEXT_KEY_DUPLICATE",
            "Context domain key IDs must be unique.", field_path="/contextDomains"))
    for context_index, context in enumerate(document.get("contexts", [])):
        for key_id, value in context["assignments"].items():
            if key_id not in context_domains or type(value) not in {type(item) for item in context_domains.get(key_id, [])} \
                    or value not in context_domains.get(key_id, []):
                invariant_diagnostics.append(_diagnostic("invariants", "CONTEXT_ASSIGNMENT_INVALID",
                    "Context assignment must use a registered key and a value in its finite domain.",
                    record_ref=f"context:{context['contextId']}",
                    field_path=f"/contexts/{context_index}/assignments/{key_id}"))

    seen_dependency_ids = set()
    for dependency_index, dependency in enumerate(document.get("dependencies", [])):
        dependency_id = dependency["dependencyId"]
        if dependency_id in seen_dependency_ids:
            invariant_diagnostics.append(_diagnostic("invariants", "DEPENDENCY_ID_DUPLICATE",
                "Dependency requirement IDs must be unique.", record_ref=f"dependency:{dependency_id}",
                field_path=f"/dependencies/{dependency_index}/dependencyId"))
        seen_dependency_ids.add(dependency_id)
    seen_resolution_ids = set()
    for resolution_index, resolution in enumerate(document.get("dependencyResolutions", [])):
        resolution_id = resolution["resolutionId"]
        if resolution_id in seen_resolution_ids:
            invariant_diagnostics.append(_diagnostic("invariants", "DEPENDENCY_RESOLUTION_ID_DUPLICATE",
                "Dependency resolution IDs must be unique.", record_ref=f"dependencyResolution:{resolution_id}",
                field_path=f"/dependencyResolutions/{resolution_index}/resolutionId"))
        seen_resolution_ids.add(resolution_id)
        count = len(resolution["providers"])
        cardinality_ok = ((resolution["status"] == "resolved" and count == 1)
                          or (resolution["status"] == "ambiguous" and count >= 2)
                          or (resolution["status"] == "unresolved" and count == 0))
        if not cardinality_ok:
            invariant_diagnostics.append(_diagnostic("invariants", "DEPENDENCY_CARDINALITY",
                "Dependency provider count must match resolved/ambiguous/unresolved status.",
                record_ref=f"dependencyResolution:{resolution_id}",
                field_path=f"/dependencyResolutions/{resolution_index}/providers"))

    facts_by_id = {fact["factId"]: fact for fact in document["facts"]}
    pending_premises = {fact_id: set(fact.get("derivation", {}).get("premiseFactIds", []))
                        for fact_id, fact in facts_by_id.items()}
    dependents: dict[str, set[str]] = {fact_id: set() for fact_id in facts_by_id}
    for fact_id, premises in pending_premises.items():
        for premise_id in premises:
            if premise_id in dependents:
                dependents[premise_id].add(fact_id)
    ready = [fact_id for fact_id, premises in pending_premises.items() if not premises]
    resolved_premises = set()
    while ready:
        resolved_id = ready.pop()
        resolved_premises.add(resolved_id)
        for dependent_id in dependents[resolved_id]:
            pending_premises[dependent_id].discard(resolved_id)
            if not pending_premises[dependent_id]:
                ready.append(dependent_id)
    if len(resolved_premises) != len(facts_by_id):
        invariant_diagnostics.append(_diagnostic("invariants", "DERIVATION_CYCLE",
            "Fact derivations must be acyclic; the cyclic dependency chain is retained in the bundle.",
            field_path="/facts"))

    condition_gaps = []
    seen_state_ids = set()
    context_domains_for_states = {item["keyId"]: item["values"] for item in document.get("contextDomains", [])}
    contexts_for_states = {item["contextId"]: item for item in document.get("contexts", [])}
    for state_index, state in enumerate(document.get("semanticStates", [])):
        state_id = state["stateId"]
        if state_id in seen_state_ids:
            invariant_diagnostics.append(_diagnostic("invariants", "STATE_ID_DUPLICATE",
                "Semantic state IDs must be unique.", record_ref=f"semanticState:{state_id}",
                field_path=f"/semanticStates/{state_index}/stateId"))
        seen_state_ids.add(state_id)
        state_ref = f"semanticState:{state_id}"
        acquisition = state["acquisition"]
        gap_diagnostics_present = any(item["severity"] == "gap" for item in state["diagnostics"])
        if acquisition in {"not_acquired", "unsupported"}:
            if state["factIds"] or not gap_diagnostics_present:
                invariant_diagnostics.append(_diagnostic("invariants", "STATE_GAP_UNEXPLAINED",
                    "Not acquired/unsupported states cannot claim facts and must explain their gap.",
                    record_ref=state_ref, field_path=f"/semanticStates/{state_index}"))
        elif acquisition == "not_applicable":
            if (not state["applicabilityReason"] or not state["evidenceIds"] or state["factIds"]):
                invariant_diagnostics.append(_diagnostic("invariants", "STATE_NOT_APPLICABLE_UNJUSTIFIED",
                    "Not-applicable states require a reason and evidence and cannot claim facts.",
                    record_ref=state_ref, field_path=f"/semanticStates/{state_index}"))
        elif acquisition == "obtained":
            for fact_id in state["factIds"]:
                fact = facts_by_id.get(fact_id)
                if fact is not None and (state["predicate"] not in {None, fact["predicate"]}
                        or (state["subject"] is not None
                            and _identity_key(state["subject"]) != _identity_key(fact["subject"]))):
                    invariant_diagnostics.append(_diagnostic("invariants", "STATE_FACT_SCOPE_MISMATCH",
                        "Obtained state fact does not match the state's subject and predicate scope.",
                        record_ref=state_ref, field_path=f"/semanticStates/{state_index}/factIds"))
        condition_parts = [state["condition"]]
        context_ref = state["subject"].get("contextRef") if state["subject"] is not None else None
        if context_ref in contexts_for_states:
            condition_parts.extend({"kind": "eq", "key": key_id, "value": value}
                                   for key_id, value in contexts_for_states[context_ref]["assignments"].items())
        satisfiable = condition_satisfiability([{"kind": "all", "conditions": condition_parts}],
                                               context_domains_for_states)
        if satisfiable["status"] == "unsat":
            invariant_diagnostics.append(_diagnostic("invariants", "STATE_CONDITION_CONTRADICTION",
                "Semantic state condition contradicts its subject context.", record_ref=state_ref,
                field_path=f"/semanticStates/{state_index}/condition"))
        elif satisfiable["status"] == "undetermined":
            condition_gaps.append(_diagnostic("invariants", satisfiable["reason"] or "CONDITION_UNDETERMINED",
                "Semantic state condition cannot be decided.", record_ref=state_ref,
                field_path=f"/semanticStates/{state_index}/condition", severity="gap"))

    contexts_by_id = {item["contextId"]: item for item in document.get("contexts", [])}
    for analysis in result["dependencyCycles"]:
        for code in analysis["diagnostics"]:
            condition_gaps.append(_diagnostic("invariants", code,
                "Dependency cycle enumeration reached its explicit resource limit; remaining cycles are unknown.",
                field_path="/dependencyResolutions", severity="gap"))
        for cycle_index, cycle in enumerate(analysis["cycles"]):
            if cycle["status"] == "undetermined":
                condition_gaps.append(_diagnostic("invariants", "CYCLE_CONDITION_UNDETERMINED",
                    f"Cycle conditions could not be decided: {cycle['reason']}.",
                    record_ref=f"cycle:{','.join(cycle['edgeIds'])}",
                    field_path=f"/dependencyCycles/{cycle_index}", severity="gap"))
    for fact_index, fact in enumerate(document["facts"]):
        condition = fact["condition"]
        conjuncts = []
        for ref in (fact["subject"], fact["value"] if isinstance(fact["value"], dict) else None):
            if ref is not None and ref.get("contextRef") in contexts_by_id:
                assignments = contexts_by_id[ref["contextRef"]]["assignments"]
                conjuncts.extend({"kind": "eq", "key": key_id, "value": value}
                                  for key_id, value in assignments.items())
        conjuncts.append(condition)
        satisfiability = condition_satisfiability([{"kind": "all", "conditions": conjuncts}], context_domains)
        if satisfiability["status"] == "unsat":
            invariant_diagnostics.append(_diagnostic("invariants", "CTX_CONTRADICTION",
                "Fact condition contains contradictory context assignments.",
                record_ref=f"fact:{fact['factId']}", field_path=f"/facts/{fact_index}/condition"))
        elif satisfiability["status"] == "undetermined":
            condition_gaps.append(_diagnostic("invariants", satisfiability["reason"] or "POTENTIAL_CONFLICT",
                "Fact condition cannot be decided within the registered context domains.",
                record_ref=f"fact:{fact['factId']}", field_path=f"/facts/{fact_index}/condition", severity="gap"))
    for dependency_index, dependency in enumerate(document.get("dependencies", [])):
        conjuncts = [dependency["condition"]]
        context_ref = dependency["consumer"].get("contextRef")
        if context_ref in contexts_by_id:
            conjuncts.extend({"kind": "eq", "key": key_id, "value": value}
                              for key_id, value in contexts_by_id[context_ref]["assignments"].items())
        satisfiability = condition_satisfiability([{"kind": "all", "conditions": conjuncts}], context_domains)
        if satisfiability["status"] == "unsat":
            invariant_diagnostics.append(_diagnostic("invariants", "DEPENDENCY_CONDITION_CONTRADICTION",
                "Dependency condition contradicts its consumer context.",
                record_ref=f"dependency:{dependency['dependencyId']}",
                field_path=f"/dependencies/{dependency_index}/condition"))
        elif satisfiability["status"] == "undetermined":
            condition_gaps.append(_diagnostic("invariants", satisfiability["reason"] or "POTENTIAL_CONFLICT",
                "Dependency condition cannot be decided within the registered context domains.",
                record_ref=f"dependency:{dependency['dependencyId']}",
                field_path=f"/dependencies/{dependency_index}/condition", severity="gap"))
    predicates = {predicate["predicateId"]: predicate for predicate in catalogs["predicates"]["predicates"]}
    for index, fact in enumerate(document["facts"]):
        record_ref = f"fact:{fact['factId']}"
        polarity = fact.get("polarity", "positive")
        basis = fact.get("negativeBasis")
        if polarity == "negative":
            if basis is None:
                invariant_diagnostics.append(_diagnostic("invariants", "NEGATIVE_BASIS_REQUIRED",
                    "A negative claim requires a finite, reviewed closure basis.", record_ref=record_ref,
                    field_path=f"/facts/{index}/negativeBasis"))
            else:
                input_ids = basis["inputIds"]
                result_ids = [item["inputId"] for item in basis["results"]]
                if (basis["condition"] != fact["condition"] or not basis["humanReviewed"]
                        or basis["unresolvedGapIds"] or len(result_ids) != len(set(result_ids))
                        or set(input_ids) != set(result_ids)):
                    invariant_diagnostics.append(_diagnostic("invariants", "NEGATIVE_BASIS_INCOMPLETE",
                        "Negative closure basis must match the fact condition and enumerate every input without unresolved gaps.",
                        record_ref=record_ref, field_path=f"/facts/{index}/negativeBasis"))
                if any(item["matched"] for item in basis["results"]):
                    invariant_diagnostics.append(_diagnostic("invariants", "NEGATIVE_CLAIM_PRESENT",
                        "The enumerated basis contains an input matching the negative claim.", record_ref=record_ref,
                        field_path=f"/facts/{index}/negativeBasis/results"))
        elif basis is not None:
            invariant_diagnostics.append(_diagnostic("invariants", "NEGATIVE_BASIS_UNEXPECTED",
                "Positive claims cannot carry a negative closure basis.", record_ref=record_ref,
                field_path=f"/facts/{index}/negativeBasis"))
        predicate = predicates.get(fact["predicate"])
        if predicate is None:
            invariant_diagnostics.append(_diagnostic("invariants", "UNSUPPORTED_PREDICATE",
                "Fact predicate is not registered in the fixed M1 catalog.", record_ref=record_ref,
                field_path=f"/facts/{index}/predicate"))
            continue
        supported_modes = (predicate["claimModes"] if is_m1 else
                           {"declaration", "specification", "static_may", "static_must", "observation", "interpretation"})
        if fact["claimMode"] not in supported_modes:
            invariant_diagnostics.append(_diagnostic("invariants", "CLAIM_MODE_UNSUPPORTED",
                "Claim mode is not supported by this predicate.", record_ref=record_ref,
                field_path=f"/facts/{index}/claimMode"))
        arguments = fact.get("arguments", [])
        argument_values = {item["role"]: item["value"] for item in arguments}
        if len(argument_values) != len(arguments):
            invariant_diagnostics.append(_diagnostic("invariants", "FACT_ARGUMENT_ROLE_DUPLICATE",
                "A fact may supply each argument role at most once.", record_ref=record_ref,
                field_path=f"/facts/{index}/arguments"))
        uses_nary = any(role["position"] == "argument" for role in predicate["roles"])
        if (uses_nary != bool(arguments) or (uses_nary and fact["value"] is not None)
                or (not uses_nary and fact["value"] is None) or (is_m1 and arguments)):
            invariant_diagnostics.append(_diagnostic("invariants", "FACT_ARGUMENT_SHAPE_MISMATCH",
                "Fact value/arguments shape must match its catalog predicate and profile.", record_ref=record_ref,
                field_path=f"/facts/{index}"))
        expected_arguments = {role["roleId"] for role in predicate["roles"] if role["position"] == "argument"}
        if set(argument_values) != expected_arguments:
            invariant_diagnostics.append(_diagnostic("invariants", "FACT_ARGUMENT_ROLES_MISMATCH",
                "A fact must supply exactly the argument roles declared by its predicate.", record_ref=record_ref,
                field_path=f"/facts/{index}/arguments"))
        for role in predicate["roles"]:
            value = (fact["subject"] if role["position"] == "subject" else
                     fact["value"] if role["position"] == "value" else argument_values.get(role["roleId"]))
            path = (f"/facts/{index}/arguments/{role['roleId']}" if role["position"] == "argument"
                    else f"/facts/{index}/{role['position']}")
            if role["valueType"] == "M1SubjectRef":
                if not isinstance(value, dict) or value.get("kind") not in role["allowedKinds"]:
                    invariant_diagnostics.append(_diagnostic("invariants", "ROLE_TYPE_MISMATCH",
                        f"Role {role['roleId']} requires a subject of kind {', '.join(role['allowedKinds'])}.",
                        record_ref=record_ref, field_path=path))
            elif role["valueType"] == "string" and (not isinstance(value, str) or not value):
                invariant_diagnostics.append(_diagnostic("invariants", "ROLE_TYPE_MISMATCH",
                    f"Role {role['roleId']} requires a non-empty string.", record_ref=record_ref,
                    field_path=path))
    if not is_m1:
        contexts_by_id = {item["contextId"]: item for item in document.get("contexts", [])}

        def effective_condition(fact):
            conditions = [fact["condition"]]
            for ref in (fact["subject"], fact["value"] if isinstance(fact["value"], dict) else None):
                context = contexts_by_id.get(ref.get("contextRef")) if ref else None
                if context:
                    conditions.extend({"kind": "eq", "key": key, "value": value}
                                       for key, value in context["assignments"].items())
            return {"kind": "all", "conditions": conditions}

        target_claims: dict[tuple[str, str, str], list[dict]] = {}
        declared_targets = set()
        for fact in document["facts"]:
            if fact["predicate"] == "build.declares_target" and isinstance(fact["value"], dict):
                target_key = _identity_key(fact["value"])
                declared_targets.add(target_key)
                target_claims.setdefault(target_key, []).append(fact)
        for target_key, claims in target_claims.items():
            for index, left in enumerate(claims):
                for right in claims[index + 1:]:
                    if _identity_key(left["subject"]) == _identity_key(right["subject"]):
                        continue
                    overlap = classify_claim_overlap(
                        {"value": _identity_key(left["subject"]), "condition": effective_condition(left)},
                        {"value": _identity_key(right["subject"]), "condition": effective_condition(right)},
                        context_domains)
                    if overlap["status"] == "compatible":
                        continue
                    code = ("BUILD_TARGET_OWNER_CONFLICT" if overlap["status"] == "conflict"
                            else "BUILD_TARGET_OWNER_UNDETERMINED")
                    severity = "error" if overlap["status"] == "conflict" else "gap"
                    for current, other in ((left, right), (right, left)):
                        invariant_diagnostics.append(_diagnostic("invariants", code,
                            "A build target has overlapping claims from different Project owners."
                            if severity == "error" else
                            "Build target owner conditions cannot be proven disjoint or overlapping.",
                            record_ref=f"fact:{current['factId']}", severity=severity,
                            related_refs=[f"fact:{other['factId']}"]))
        for index, fact in enumerate(document["facts"]):
            if fact["predicate"] == "build.alias_of" and isinstance(fact["value"], dict) \
                    and _identity_key(fact["value"]) not in declared_targets:
                invariant_diagnostics.append(_diagnostic("invariants", "ALIAS_TARGET_UNDECLARED",
                    "A build alias must resolve to a target declared in this fact set.",
                    record_ref=f"fact:{fact['factId']}", field_path=f"/facts/{index}/value"))
    assessments = {item["assessmentId"]: item for item in document["assessments"]}
    supersedes_edges: dict[str, list[str]] = {}
    for index, assessment in enumerate(document["assessments"]):
        record_ref = f"assessment:{assessment['assessmentId']}"
        path = f"/assessments/{index}"
        if assessment["declaration"]["kind"] != "SourceDeclaration":
            invariant_diagnostics.append(_diagnostic("invariants", "ASSESSMENT_DECLARATION_KIND",
                "Project-boundary assessments must reference a SourceDeclaration.", record_ref=record_ref,
                field_path=f"{path}/declaration/kind"))
        if any(project["kind"] != "Project" for project in assessment["projects"]):
            invariant_diagnostics.append(_diagnostic("invariants", "ASSESSMENT_PROJECT_KIND",
                "Project-boundary candidates must all be Project subjects.", record_ref=record_ref,
                field_path=f"{path}/projects"))
        count = len(assessment["projects"])
        expected_count = (count == 1 if assessment["status"] == "resolved"
                          else count >= 2 if assessment["status"] == "ambiguous" else count == 0)
        if not expected_count:
            invariant_diagnostics.append(_diagnostic("invariants", "ASSESSMENT_CARDINALITY",
                "resolved requires one project, ambiguous at least two, and unresolved none.",
                record_ref=record_ref, field_path=f"{path}/projects"))
        supersedes_edges[assessment["assessmentId"]] = list(assessment["supersedes"])
        for old_id in assessment["supersedes"]:
            old = assessments.get(old_id)
            if old is not None and (_identity_key(old["declaration"]) != _identity_key(assessment["declaration"])
                                    or old["ruleId"] != assessment["ruleId"]):
                invariant_diagnostics.append(_diagnostic("invariants", "SUPERSEDES_KEY_MISMATCH",
                    "An assessment may supersede only an assessment for the same declaration and rule.",
                    record_ref=record_ref, field_path=f"{path}/supersedes"))

    visiting: set[str] = set()
    visited: set[str] = set()

    def has_supersedes_cycle(assessment_id: str) -> bool:
        if assessment_id in visiting:
            return True
        if assessment_id in visited:
            return False
        visiting.add(assessment_id)
        for old_id in supersedes_edges.get(assessment_id, []):
            if old_id in supersedes_edges and has_supersedes_cycle(old_id):
                return True
        visiting.remove(assessment_id)
        visited.add(assessment_id)
        return False

    for assessment_id in supersedes_edges:
        if has_supersedes_cycle(assessment_id):
            invariant_diagnostics.append(_diagnostic("invariants", "SUPERSEDES_CYCLE",
                "Assessment supersedes lineage must be acyclic.", record_ref=f"assessment:{assessment_id}",
                field_path=f"/assessments/{list(supersedes_edges).index(assessment_id)}/supersedes"))
            break
    observation_errors = []
    observations_by_id = {}
    if source_observations is not None:
        if (not isinstance(source_observations, dict) or set(source_observations) != {"items"}
                or not isinstance(source_observations.get("items"), list)):
            observation_errors.append(_diagnostic("invariants", "OBSERVATION_INVALID",
                "Source observations must have exactly one items array.", field_path="/source_observations"))
        else:
            for index, item in enumerate(source_observations["items"]):
                if (not isinstance(item, dict) or set(item) != {"evidenceId", "status", "observedSha256"}
                        or not isinstance(item.get("evidenceId"), str) or not item["evidenceId"]
                        or not isinstance(item.get("status"), str)
                        or item.get("status") not in {"verified", "unchecked", "mismatch"}
                        or (item.get("observedSha256") is not None and
                            (not isinstance(item["observedSha256"], str)
                             or len(item["observedSha256"]) != 64
                             or any(char not in "0123456789abcdef" for char in item["observedSha256"])) )):
                    observation_errors.append(_diagnostic("invariants", "OBSERVATION_INVALID",
                        "Observation item has an invalid shape or digest.", field_path=f"/source_observations/items/{index}"))
                    continue
                if item["evidenceId"] in observations_by_id:
                    observation_errors.append(_diagnostic("invariants", "OBSERVATION_INVALID",
                        "Observation evidence IDs must be unique.", field_path=f"/source_observations/items/{index}/evidenceId"))
                observations_by_id[item["evidenceId"]] = item
                if (item["status"] == "verified") != (item["observedSha256"] is not None):
                    if item["status"] != "mismatch" or item["observedSha256"] is None:
                        observation_errors.append(_diagnostic("invariants", "OBSERVATION_INVALID",
                            "verified and mismatch require an observed digest; unchecked requires null.",
                            field_path=f"/source_observations/items/{index}"))
                elif item["status"] == "mismatch" and item["observedSha256"] is None:
                    observation_errors.append(_diagnostic("invariants", "OBSERVATION_INVALID",
                        "mismatch requires an observed digest.", field_path=f"/source_observations/items/{index}"))
    evidence_by_id = {item["evidenceId"]: item for item in document["evidence"]}
    for evidence_id, observation in observations_by_id.items():
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            observation_errors.append(_diagnostic("invariants", "OBSERVATION_REF_MISSING",
                "Observation must reference evidence in this bundle.", record_ref=f"evidence:{evidence_id}",
                field_path="/source_observations/items"))
        elif observation["status"] == "verified" and observation["observedSha256"] != evidence["sha256"]:
            observation_errors.append(_diagnostic("invariants", "INPUT_MISMATCH",
                "Verified source digest does not match the evidence record.", record_ref=f"evidence:{evidence_id}"))
        elif observation["status"] == "mismatch" and observation["observedSha256"] == evidence["sha256"]:
            observation_errors.append(_diagnostic("invariants", "OBSERVATION_INVALID",
                "A mismatch observation must differ from the evidence digest.", record_ref=f"evidence:{evidence_id}"))
        elif observation["status"] == "mismatch":
            observation_errors.append(_diagnostic("invariants", "INPUT_MISMATCH",
                "Observed source digest differs from the evidence record.", record_ref=f"evidence:{evidence_id}"))
    if observation_errors:
        invariant_diagnostics.extend(observation_errors)
    gap_diagnostics = []
    for evidence_id in evidence_by_id:
        observation = observations_by_id.get(evidence_id)
        if observation is None or observation["status"] == "unchecked":
            gap_diagnostics.append(_diagnostic("invariants", "EVIDENCE_UNCHECKED",
                "Evidence source was not verified by the caller.", record_ref=f"evidence:{evidence_id}", severity="gap"))
    if not is_m1:
        for index, fact in enumerate(document["facts"]):
            if fact["predicate"] != "build.observed_artifact":
                continue
            qualifying = [evidence_id for evidence_id in fact["evidenceIds"]
                          if evidence_id in evidence_by_id and evidence_by_id[evidence_id]["source"] == "tool_output"
                          and observations_by_id.get(evidence_id, {}).get("status") == "verified"]
            if fact["claimMode"] != "observation" or not qualifying:
                invariant_diagnostics.append(_diagnostic("invariants", "ARTIFACT_OBSERVATION_UNVERIFIED",
                    "An observed artifact requires observation claim mode and verified tool-output evidence.",
                    record_ref=f"fact:{fact['factId']}", field_path=f"/facts/{index}/evidenceIds"))

    coverage_by_id = {item["coverageId"]: item for item in document["coverage"]}
    coverage_edges = {}
    for index, coverage in enumerate(document["coverage"]):
        record_ref = f"coverage:{coverage['coverageId']}"
        path = f"/coverage/{index}"
        coverage_edges[coverage["coverageId"]] = list(coverage["supersedes"])
        unchecked_coverage_evidence = [evidence_id for evidence_id in coverage["evidenceIds"]
                                       if evidence_id not in observations_by_id
                                       or observations_by_id[evidence_id]["status"] == "unchecked"]
        if coverage["complete"] and (unchecked_coverage_evidence
                                      or any(item["severity"] in {"gap", "error"} for item in coverage["diagnostics"])):
            invariant_diagnostics.append(_diagnostic("invariants", "COVERAGE_COMPLETE_WITH_GAPS",
                "Complete coverage cannot contain gap or error diagnostics.", record_ref=record_ref,
                field_path=f"{path}/complete"))
        for old_id in coverage["supersedes"]:
            old = coverage_by_id.get(old_id)
            if old is not None and (old["selector"] != coverage["selector"]
                                    or (None if old["subject"] is None else _identity_key(old["subject"]))
                                    != (None if coverage["subject"] is None else _identity_key(coverage["subject"]))):
                invariant_diagnostics.append(_diagnostic("invariants", "SUPERSEDES_KEY_MISMATCH",
                    "Coverage may supersede only coverage for the same selector and subject.",
                    record_ref=record_ref, field_path=f"{path}/supersedes"))
            if old is not None:
                available_keys = {_diagnostic_key(item) for item in old["diagnostics"]
                                  if item["severity"] in {"gap", "error"}}
                if not set(coverage["resolvedDiagnosticKeys"]).issubset(available_keys):
                    invariant_diagnostics.append(_diagnostic("invariants", "COVERAGE_DIAGNOSTIC_KEY_MISMATCH",
                        "Resolved diagnostic keys must identify diagnostics on a superseded coverage record.",
                        record_ref=record_ref, field_path=f"{path}/resolvedDiagnosticKeys"))

    visiting = set()
    visited = set()

    def has_coverage_cycle(coverage_id):
        if coverage_id in visiting:
            return True
        if coverage_id in visited:
            return False
        visiting.add(coverage_id)
        for old_id in coverage_edges.get(coverage_id, []):
            if old_id in coverage_edges and has_coverage_cycle(old_id):
                return True
        visiting.remove(coverage_id)
        visited.add(coverage_id)
        return False

    for coverage_id in coverage_edges:
        if has_coverage_cycle(coverage_id):
            invariant_diagnostics.append(_diagnostic("invariants", "SUPERSEDES_CYCLE",
                "Coverage supersedes lineage must be acyclic.", record_ref=f"coverage:{coverage_id}"))
            break
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
        result["stages"]["invariants"] = ("fail" if any(item["severity"] == "error" for item in invariant_diagnostics)
                                            else "partial")
        result["diagnostics"] = invariant_diagnostics + gap_diagnostics + condition_gaps
        result["valid"] = result["stages"]["invariants"] != "fail"
        return result
    result["stages"]["invariants"] = "partial"
    claim_groups: dict[tuple, list[dict]] = {}
    predicates_by_id = {item["predicateId"]: item for item in catalogs["predicates"]["predicates"]}
    for fact in document["facts"]:
        predicate = predicates_by_id.get(fact["predicate"])
        if predicate is None or predicate["claimCardinality"] != "single_value_per_context":
            continue
        value_key = _identity_key(fact["value"]) if isinstance(fact["value"], dict) else fact["value"]
        key = (fact["predicate"], _identity_key(fact["subject"]), fact["claimMode"])
        claim_groups.setdefault(key, []).append({"recordRef": f"fact:{fact['factId']}",
            "value": value_key, "condition": fact["condition"], "fact": fact})
    conflict_diagnostics = []
    for claims in claim_groups.values():
        for index, left in enumerate(claims):
            for right in claims[index + 1:]:
                if left["value"] == right["value"]:
                    continue
                left_condition = {"kind": "all", "conditions": [left["condition"]]}
                right_condition = {"kind": "all", "conditions": [right["condition"]]}
                for ref in (left["fact"]["subject"], left["fact"]["value"] if isinstance(left["fact"]["value"], dict) else None):
                    if ref is not None and ref.get("contextRef") in contexts_by_id:
                        left_condition["conditions"].extend({"kind": "eq", "key": key_id, "value": value}
                            for key_id, value in contexts_by_id[ref["contextRef"]]["assignments"].items())
                for ref in (right["fact"]["subject"], right["fact"]["value"] if isinstance(right["fact"]["value"], dict) else None):
                    if ref is not None and ref.get("contextRef") in contexts_by_id:
                        right_condition["conditions"].extend({"kind": "eq", "key": key_id, "value": value}
                            for key_id, value in contexts_by_id[ref["contextRef"]]["assignments"].items())
                overlap = classify_claim_overlap({"value": left["value"], "condition": left_condition},
                                                 {"value": right["value"], "condition": right_condition},
                                                 context_domains)
                if overlap["status"] not in {"conflict", "potential_conflict"}:
                    continue
                conflict = overlap["status"] == "conflict"
                code = "SINGLE_VALUE_CONFLICT" if conflict else "POTENTIAL_CONFLICT"
                severity = "conflict" if conflict else "gap"
                for current, other in ((left, right), (right, left)):
                    conflict_diagnostics.append(_diagnostic("invariants", code,
                        "Different values are retained for overlapping single-valued claims." if conflict
                        else "Different single-valued claims may overlap under an unsupported condition.",
                        record_ref=current["recordRef"], severity=severity,
                        related_refs=[other["recordRef"]]))
    result["diagnostics"] = gap_diagnostics + condition_gaps + conflict_diagnostics
    result["valid"] = True
    result["consistency"] = "conflicting" if any(item["severity"] == "conflict"
                                                  for item in conflict_diagnostics) else "undetermined"
    return result
