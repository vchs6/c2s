"""Translate the current project-discovery query projection into M1 records."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from .validation import register_m1, semantic_model_catalogs


def project_query_to_m1(query_result, registrations: list[dict] | None = None) -> dict:
    """Project E0 project and workspace facts without inventing evidence or ownership.

    Workspace membership currently comes from Cargo metadata, whose output artifact is
    not retained by the query API. Those evidence records therefore remain unchecked.
    """
    root = Path(query_result.root).resolve(strict=True)
    from c2s_skill.inventory import source_fingerprint

    if source_fingerprint(root) != query_result.source_digest:
        raise ValueError("project sources changed after the query scan; rerun the query before projecting M1")
    registration_records = list(registrations or [])
    domain_id = "c2s-m1-project-discovery"
    refs: dict[tuple[str, str], dict] = {}
    evidence_records: dict[str, dict] = {}
    observations: dict[str, dict] = {}
    artifacts: dict[str, dict] = {}
    facts = []
    workspace_metadata = None

    workspace_facts = [fact for fact in query_result.facts if fact.kind == "workspace_member"]
    if workspace_facts:
        cargo = os.environ.get("CARGO") or shutil.which("cargo")
        manifest = root / "Cargo.toml"
        if cargo and manifest.is_file() and not manifest.is_symlink():
            try:
                completed = subprocess.run(
                    [cargo, "metadata", "--format-version", "1", "--no-deps", "--offline",
                     "--manifest-path", str(manifest)], cwd=root, capture_output=True, text=True,
                    timeout=20, check=True)
                metadata = json.loads(completed.stdout)
                package_names = sorted(item["name"] for item in metadata.get("packages", []))
                if package_names != sorted(fact.name for fact in workspace_facts):
                    raise ValueError("Cargo workspace results changed since the query scan")
                tool_version = subprocess.run([cargo, "--version"], capture_output=True, text=True,
                                              timeout=3, check=True).stdout.strip()
                workspace_metadata = (completed.stdout, tool_version)
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
                workspace_metadata = None

    def register(kind: str, source_key: str, evidence_id: str) -> dict:
        result = register_m1(domain_id, registration_records, kind, source_key, [evidence_id])
        if "ref" not in result:
            raise ValueError(result["message"])
        if not any(item.get("sourceKey") == source_key for item in registration_records):
            registration_records.append(result)
        else:
            for index, item in enumerate(registration_records):
                if item.get("sourceKey") == source_key:
                    registration_records[index] = result
                    break
        return result["ref"]

    def add_evidence(fact) -> tuple[str, dict]:
        if fact.kind == "workspace_member" and workspace_metadata is not None:
            output, tool_version = workspace_metadata
            output_bytes = output.encode("utf-8")
            digest = hashlib.sha256(output_bytes).hexdigest()
            artifact_id = digest
            artifacts[artifact_id] = {"artifactId": artifact_id, "mediaType": "application/json",
                                      "sha256": digest, "content": output}
            evidence_id = hashlib.sha256(
                f"{fact.id}\0cargo-metadata\0{digest}".encode("utf-8")).hexdigest()
            evidence = {"evidenceId": evidence_id, "source": "tool_output", "path": None,
                        "artifactId": artifact_id, "originalPath": "Cargo metadata --no-deps output",
                        "sha256": digest, "startByte": 0, "endByte": len(output_bytes),
                        "method": "cargo-metadata", "toolName": "cargo", "toolVersion": tool_version}
            evidence_records[evidence_id] = evidence
            observations[evidence_id] = {"evidenceId": evidence_id, "status": "verified",
                                         "observedSha256": digest}
            return evidence_id, evidence
        relative = Path(fact.path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"fact source path escapes project root: {fact.path}")
        source_path = root / relative
        cursor = source_path
        while cursor != root and root in cursor.parents:
            if cursor.is_symlink():
                raise ValueError(f"fact source path traverses symlink: {fact.path}")
            cursor = cursor.parent
        source = source_path.read_bytes()
        if fact.end_byte > len(source) or fact.start_byte > fact.end_byte:
            raise ValueError(f"fact source span is outside the source file: {fact.path}")
        digest = hashlib.sha256(source).hexdigest()
        evidence_id = hashlib.sha256(
            f"{fact.path}\0{fact.start_byte}\0{fact.end_byte}\0{digest}".encode("utf-8")).hexdigest()
        evidence = {"evidenceId": evidence_id, "source": "input", "path": fact.path,
                    "artifactId": None, "originalPath": fact.path, "sha256": digest,
                    "startByte": fact.start_byte, "endByte": fact.end_byte,
                    "method": fact.claim_mode, "toolName": None, "toolVersion": None}
        evidence_records[evidence_id] = evidence
        if fact.kind == "workspace_member":
            observations[evidence_id] = {"evidenceId": evidence_id, "status": "unchecked", "observedSha256": None}
        else:
            observations[evidence_id] = {"evidenceId": evidence_id, "status": "verified", "observedSha256": digest}
        return evidence_id, evidence

    workspace_ref = None
    for fact in query_result.facts:
        if fact.kind not in {"project_name", "language_declared", "workspace_member"}:
            continue
        evidence_id, _ = add_evidence(fact)
        if fact.kind == "workspace_member":
            if workspace_ref is None:
                workspace_ref = register("NativeWorkspace", "workspace:" + str(root), evidence_id)
            package_key = "package:" + (fact.owner or fact.name)
            subject = register("PackageSpecification", package_key, evidence_id)
            predicate = "workspace.member"
            value = subject
            subject = workspace_ref
        else:
            subject = register("Project", "project:" + fact.subject_id, evidence_id)
            predicate = "project.name" if fact.kind == "project_name" else "project.language_declared"
            value = fact.name
        facts.append({"factId": fact.id, "predicate": predicate, "subject": subject, "value": value,
                      "claimMode": "declaration", "condition": {"kind": "true"},
                      "evidenceIds": [evidence_id]})

    if source_fingerprint(root) != query_result.source_digest:
        raise ValueError("project sources changed during M1 projection; rerun the query")

    diagnostic_rows = []
    for gap in query_result.gaps:
        code = gap.reason.split(":", 1)[0]
        diagnostic_rows.append({"code": code, "severity": "gap", "recordId": gap.selector,
                                "path": None, "message": gap.reason})
    for observation in observations.values():
        if observation["status"] == "unchecked":
            diagnostic_rows.append({"code": "EVIDENCE_UNCHECKED", "severity": "gap",
                                    "recordId": observation["evidenceId"], "path": None,
                                    "message": "Cargo metadata output attachment was not retained by the query API."})
    checked_paths = sorted({fact.path for fact in query_result.facts
                            if fact.kind in {"project_name", "language_declared", "workspace_member"}})
    coverage_id = hashlib.sha256(
        (query_result.source_digest + "\0project+workspace-members").encode("utf-8")).hexdigest()
    coverage_complete = query_result.complete and not any(
        observation["status"] != "verified" for observation in observations.values())
    coverage = {"coverageId": coverage_id, "selector": "project+workspace-members", "subject": None,
                "checkedPaths": checked_paths, "evidenceIds": sorted(evidence_records),
                "complete": coverage_complete, "supersedes": [], "resolvedDiagnosticKeys": [],
                "diagnostics": diagnostic_rows}
    bundle = {"version": "1.0.0", "profile": "m1-project-discovery-1",
              "registrations": registration_records, "assessments": [], "facts": facts,
              "evidence": list(evidence_records.values()), "coverage": [coverage], "diagnostics": []}
    return {"bundle": bundle, "artifacts": list(artifacts.values()),
            "sourceObservations": {"items": list(observations.values())}}


def project_algorithm(document: dict, algorithm_ref: dict) -> dict:
    """Render one structured algorithm without adding behavior beyond its records."""
    algorithm_id = algorithm_ref.get("algorithm_id") if isinstance(algorithm_ref, dict) else None
    candidates = [item for item in document.get("algorithms", [])
                  if isinstance(item, dict) and item.get("algorithm_id") == algorithm_id]
    if len(candidates) != 1:
        raise ValueError("algorithm_ref must identify exactly one algorithm")
    algorithm = candidates[0]
    from c2s_skill.algorithm import validate_algorithms

    diagnostics = validate_algorithms({"schema_version": document.get("schema_version"),
                                       "algorithms": [algorithm]})
    if diagnostics:
        raise ValueError(f"algorithm contract is invalid: {diagnostics[0]['code']}")
    body = algorithm["body"]
    regions = {item["region_id"]: item for item in body["regions"]}

    def depth(region_id: str | None) -> int:
        result = 0
        visited = set()
        while region_id in regions and regions[region_id].get("parent_region_id") is not None:
            if region_id in visited:
                break
            visited.add(region_id)
            region_id = regions[region_id]["parent_region_id"]
            result += 1
        return result

    lines = [f"Algorithm: {algorithm['problem']}", f"Purpose: {algorithm['purpose']}"]
    mappings = []
    for step in body["steps"]:
        source = step.get("source")
        location = (f"{source['path']}:{source['start_byte']}-{source['end_byte']}"
                    if isinstance(source, dict) else "source unavailable")
        attributes = step.get("attributes", {})
        operation = attributes.get("operation") if isinstance(attributes, dict) else None
        suffix = f" — {operation}" if operation else ""
        if step.get("kind") == "opaque" and step.get("impact"):
            suffix += f" — {step['impact']}"
        line = "  " * depth(step.get("region_id")) + f"- [{step['kind']}] {step['step_id']} ({location}){suffix}"
        if step.get("kind") == "opaque" and step.get("unknowns"):
            line += f" [unknown: {', '.join(step['unknowns'])}]"
        lines.append(line)
        mappings.append({"stepId": step["step_id"], "startLine": len(lines), "endLine": len(lines)})
    for label, edge_kind in (("Control", "control_edges"), ("Data", "data_edges")):
        for edge in body[edge_kind]:
            if edge_kind == "control_edges":
                relation = f"{edge['kind']} / {edge['condition']['kind']}"
            else:
                relation = edge["role"]
            lines.append(f"{label}: {edge['from_step']} -> {edge['to_step']} ({relation})")
    gaps = list(algorithm.get("omissions", []))
    for item in algorithm["contract"]["coverage"]:
        if item["state"] != "complete":
            gaps.append({"category": item["category"], "reason": item.get("reason", item["state"])})
    for item in gaps:
        lines.append(f"Gap: {item.get('reason', item.get('category', 'unspecified'))}")
    return {"text": "\n".join(lines), "stepMappings": mappings, "gaps": gaps}


def check_source_coverage(document: dict, checklist: dict) -> dict:
    """Check a reviewed source checklist against body steps, effects or declared gaps.

    This function does not inspect source files or decide whether the checklist is
    exhaustive; it only validates the submitted human-reviewed mapping.
    """
    algorithm = next((item for item in document.get("algorithms", []) if isinstance(item, dict)), {})
    step_ids = {step.get("step_id") for step in algorithm.get("body", {}).get("steps", [])
                if isinstance(step, dict)}
    effect_count = len(algorithm.get("contract", {}).get("effects", []))
    raw_items = checklist.get("items") if isinstance(checklist, dict) else None
    items = raw_items if isinstance(raw_items, list) else []
    reviewed = isinstance(checklist, dict) and checklist.get("reviewed") is True
    uncovered = []
    declared_gaps = []
    if not items:
        uncovered.append({"itemId": None, "reason": "source checklist must contain at least one reviewed item"})
    if raw_items is not None and not isinstance(raw_items, list):
        uncovered.append({"itemId": None, "reason": "checklist items must be an array"})
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            uncovered.append({"itemId": None, "reason": "checklist item has invalid shape"})
            continue
        item_id = item.get("itemId")
        steps = item.get("stepIds", [])
        effects = item.get("effectIndices", [])
        gap_reason = item.get("gapReason")
        mapped = (isinstance(steps, list) and any(step_id in step_ids for step_id in steps)
                  or isinstance(effects, list) and any(type(index) is int and 0 <= index < effect_count
                                                       for index in effects))
        valid = bool(item_id and isinstance(item.get("description"), str) and
                     ((mapped and all(step_id in step_ids for step_id in steps)
                       and all(type(index) is int and 0 <= index < effect_count for index in effects))
                      or (not mapped and isinstance(gap_reason, str) and bool(gap_reason))))
        if not reviewed or not valid:
            uncovered.append({"itemId": item_id, "reason": "source checklist is unreviewed" if not reviewed
                              else "item has no valid Step/effect mapping or explicit gap"})
        if isinstance(gap_reason, str) and gap_reason:
            declared_gaps.append({"itemId": item_id, "reason": gap_reason})
    return {"reviewed": reviewed, "uncoveredItems": uncovered, "declaredGaps": declared_gaps}


_QUERY_KIND_PREDICATES = {
    "project_name": "project.name", "language_declared": "project.language_declared",
    "workspace_member": "workspace.member", "module": "module.declared",
    "struct": "type.declared", "class": "type.declared", "enum": "type.declared",
    "trait": "type.declared", "type_alias": "type.declared", "field": "member.declared",
    "variant": "member.declared", "impl": "implementation.block", "function": "function.declared",
    "import": "import.declared", "constant": "constant.declared", "constant_item": "constant.declared",
    "static_item": "constant.declared", "behavior_contract": "behavior.contract",
    "algorithm_step": "behavior.algorithm_step", "local_binding": "binding.local",
}


def project_query_to_semantic_model(query_result, catalogs: dict | None = None) -> dict:
    """Project every currently supported query fact into the full semantic profile.

    This maps existing Python/Rust syntax facts; it does not add type/call binding,
    project ownership inference, or runtime observations.
    """
    root = Path(query_result.root).resolve(strict=True)
    from c2s_skill.inventory import source_fingerprint

    if source_fingerprint(root) != query_result.source_digest:
        raise ValueError("project sources changed after the query scan; rerun before semantic projection")
    catalogs = catalogs or semantic_model_catalogs()
    supported_predicates = {item["predicateId"] for item in catalogs["predicates"]["predicates"]}
    domain_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    registrations_by_key: dict[tuple[str, str], dict] = {}
    evidence_by_id: dict[str, dict] = {}
    sources_by_path: dict[str, tuple[bytes, str]] = {}
    observations_by_id: dict[str, dict] = {}
    facts = []
    fact_presentation: dict[str, bool] = {}
    refs_by_key: dict[tuple[str, str], dict] = {}
    diagnostics = []

    def subject_ref(kind: str, local_id: str, source_key: str, evidence_id: str) -> dict:
        key = (kind, local_id)
        if key not in refs_by_key:
            refs_by_key[key] = {"identity": {"authority": "c2s-analysis", "domainId": domain_id,
                                                "localId": local_id}, "kind": kind}
        ref = refs_by_key[key]
        registration_key = (kind, source_key)
        if registration_key not in registrations_by_key:
            registrations_by_key[registration_key] = {"ref": ref, "sourceKey": source_key,
                                                       "evidenceIds": []}
        registration = registrations_by_key[registration_key]
        if evidence_id not in registration["evidenceIds"]:
            registration["evidenceIds"].append(evidence_id)
        return ref

    def evidence_for(fact) -> tuple[str, dict]:
        source_path = (root / fact.path).resolve(strict=True)
        if root not in source_path.parents and source_path != root:
            raise ValueError(f"fact source escapes project root: {fact.path}")
        cursor = source_path
        while cursor != root:
            if cursor.is_symlink():
                raise ValueError(f"fact source traverses a symlink: {fact.path}")
            cursor = cursor.parent
        source_pair = sources_by_path.get(fact.path)
        if source_pair is None:
            source = source_path.read_bytes()
            source_pair = (source, hashlib.sha256(source).hexdigest())
            sources_by_path[fact.path] = source_pair
        source, digest = source_pair
        if not (0 <= fact.start_byte <= fact.end_byte <= len(source)):
            raise ValueError(f"fact source span is outside source file: {fact.path}")
        evidence_id = hashlib.sha256(
            f"{fact.path}\0{fact.start_byte}\0{fact.end_byte}\0{digest}".encode("utf-8")).hexdigest()
        evidence = {"evidenceId": evidence_id, "source": "input", "path": fact.path,
                    "artifactId": None, "originalPath": fact.path, "sha256": digest,
                    "startByte": fact.start_byte, "endByte": fact.end_byte,
                    "method": fact.claim_mode, "toolName": None, "toolVersion": None}
        evidence_by_id[evidence_id] = evidence
        if fact.kind == "workspace_member":
            observations_by_id[evidence_id] = {"evidenceId": evidence_id, "status": "unchecked",
                                               "observedSha256": None}
        else:
            observations_by_id[evidence_id] = {"evidenceId": evidence_id, "status": "verified",
                                               "observedSha256": digest}
        return evidence_id, evidence

    for fact in query_result.facts:
        predicate_id = _QUERY_KIND_PREDICATES.get(fact.kind)
        if predicate_id is None or predicate_id not in supported_predicates:
            diagnostics.append({"code": "FACT_KIND_UNMAPPED", "severity": "gap", "recordId": fact.id,
                                "path": fact.path, "message": f"No semantic predicate is registered for {fact.kind}."})
            continue
        evidence_id, _ = evidence_for(fact)
        if fact.kind in {"project_name", "language_declared"}:
            identity_kind = "Project"
            local_id = fact.subject_id or hashlib.sha256(f"project:{root}".encode()).hexdigest()
            source_key = "project:" + local_id
        elif fact.kind == "workspace_member":
            workspace_local_id = hashlib.sha256(f"workspace:{root}".encode()).hexdigest()
            subject = subject_ref("NativeWorkspace", workspace_local_id, "workspace:" + str(root), evidence_id)
            package_key = fact.owner or fact.name
            package_local_id = hashlib.sha256(f"package:{domain_id}:{package_key}".encode()).hexdigest()
            value = subject_ref("PackageSpecification", package_local_id, "package:" + package_key, evidence_id)
            identity_kind = None
            local_id = None
            source_key = None
        else:
            identity_kind = "SourceDeclaration"
            local_id = fact.subject_id or hashlib.sha256(
                f"{fact.kind}\0{fact.path}\0{fact.start_byte}\0{fact.name}".encode()).hexdigest()
            source_key = "source:" + local_id
        if fact.kind != "workspace_member":
            subject = subject_ref(identity_kind, local_id, source_key, evidence_id)
            value = (fact.text or fact.name) if fact.kind in {"behavior_contract", "algorithm_step"} else fact.name
        fact_id = hashlib.sha256(f"{fact.id}\0{predicate_id}\0{fact.start_byte}".encode()).hexdigest()
        claim_mode = {"syntax": "declaration", "documentation": "specification",
                      "cargo_metadata": "declaration"}.get(fact.claim_mode, "interpretation")
        facts.append({"factId": fact_id, "predicate": predicate_id, "subject": subject, "value": value,
            "claimMode": claim_mode, "condition": {"kind": "true"}, "evidenceIds": [evidence_id],
            "sourceMetadata": {"kind": fact.kind, "layer": fact.layer, "owner": fact.owner,
                               "text": fact.text, "evidenceIncluded": fact.evidence_included}})
        fact_presentation[fact_id] = fact.evidence_included

    if source_fingerprint(root) != query_result.source_digest:
        raise ValueError("project sources changed during semantic projection; rerun the query")
    for gap in query_result.gaps:
        diagnostics.append({"code": gap.reason.split(":", 1)[0], "severity": "gap",
                            "recordId": gap.selector, "path": None, "message": gap.reason})
    for observation in observations_by_id.values():
        if observation["status"] == "unchecked":
            diagnostics.append({"code": "EVIDENCE_UNCHECKED", "severity": "gap",
                "recordId": observation["evidenceId"], "path": None,
                "message": "Workspace metadata evidence has no retained tool-output artifact."})
    if query_result.facts and not facts:
        diagnostics.append({"code": "NO_SUPPORTED_FACTS_PROJECTED", "severity": "gap", "recordId": None,
                            "path": None, "message": "No query facts could be represented by the supplied catalog."})
    if not query_result.facts:
        diagnostics.append({"code": "NO_FACTS_RETURNED", "severity": "gap", "recordId": None,
                            "path": None, "message": "An empty query result does not prove semantic absence."})
    checked_paths = sorted(entry.path for entry in query_result.inventory
                           if entry.kind == "file" and entry.path.endswith((".py", ".rs"))
                           and entry.state == "readable")
    selector = "+".join(query_result.requested)
    coverage_id = hashlib.sha256(f"{query_result.source_digest}\0{selector}".encode()).hexdigest()
    complete = query_result.complete and bool(facts) and not any(
        item["status"] != "verified" for item in observations_by_id.values()) and not diagnostics
    coverage = {"coverageId": coverage_id, "selector": selector, "subject": None,
        "checkedPaths": checked_paths, "evidenceIds": sorted(evidence_by_id), "complete": complete,
        "supersedes": [], "resolvedDiagnosticKeys": [], "diagnostics": diagnostics}
    state_diagnostics = [item for item in diagnostics if item["severity"] in {"gap", "error"}]
    semantic_states = []
    if facts:
        for included in (True, False):
            selected_facts = [fact for fact in facts if fact_presentation[fact["factId"]] is included]
            if not selected_facts:
                continue
            semantic_states.append({"stateId": hashlib.sha256(
                    f"{coverage_id}\0presentation:{included}".encode()).hexdigest(),
                "selector": selector, "subject": None, "predicate": None, "condition": {"kind": "true"},
                "presentation": "expanded" if included else "ref_only", "acquisition": "obtained",
                "factIds": [fact["factId"] for fact in selected_facts], "applicabilityReason": None,
                "evidenceIds": sorted({evidence_id for fact in selected_facts for evidence_id in fact["evidenceIds"]}),
                "diagnostics": state_diagnostics})
    else:
        semantic_states.append({"stateId": hashlib.sha256(f"{coverage_id}\0empty".encode()).hexdigest(),
            "selector": selector, "subject": None, "predicate": None, "condition": {"kind": "true"},
            "presentation": "ref_only", "acquisition": "not_acquired", "factIds": [],
            "applicabilityReason": None, "evidenceIds": [], "diagnostics": state_diagnostics})
    bundle = {"version": "1.0.0", "profile": "semantic-fact-model-1",
        "registrations": sorted(registrations_by_key.values(), key=lambda item: item["sourceKey"]),
        "assessments": [], "facts": facts, "evidence": list(evidence_by_id.values()),
        "coverage": [coverage], "diagnostics": [], "semanticStates": semantic_states}
    return {"bundle": bundle, "artifacts": [],
            "sourceObservations": {"items": list(observations_by_id.values())}}
