"""历史投影测试侧冻结辅助，不由产品包导出。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from _historical_validation import register_m1, semantic_model_catalogs


def project_query_to_m1(query_result, registrations: list[dict] | None = None,
                        identity_domain: str | None = None) -> dict:
    """Project E0 project and workspace facts without inventing evidence or ownership.

    Workspace membership currently comes from Cargo metadata, whose output artifact is
    not retained by the query API. Those evidence records therefore remain unchecked.
    """
    root = Path(query_result.root).resolve(strict=True)
    from c2s_skill.inventory import source_fingerprint

    if source_fingerprint(root) != query_result.source_digest:
        raise ValueError("project sources changed after the query scan; rerun the query before projecting M1")
    registration_records = list(registrations or [])
    domain_id = identity_domain or "c2s-m1-project-discovery"
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


