"""证据驱动的语义实体候选构造；候选身份尚不是持久实体身份。"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

from .acquisition import (Fact, ProjectScan, SourceConstruct, analysis_profile_digest,
                          scan_project)
from .inventory import source_fingerprint


_MODULE_HEADINGS = {"modules", "module", "模块", "组件模块"}
_CAPABILITY_HEADINGS = {"features", "feature", "capabilities", "capability", "功能", "功能特性", "能力"}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fact_evidence(root: Path, fact: Fact) -> dict:
    path = Path(fact.path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"源码证据路径越出项目范围：{fact.path}")
    source = (root / path).read_bytes()
    if fact.start_byte < 0 or fact.end_byte < fact.start_byte or fact.end_byte > len(source):
        raise ValueError(f"源码证据跨度无效：{fact.path}:{fact.start_byte}-{fact.end_byte}")
    sha = hashlib.sha256(source).hexdigest()
    evidence_id = _digest(f"{fact.path}\0{fact.start_byte}\0{fact.end_byte}\0{sha}")
    return {"evidenceId": evidence_id, "source": "input", "description": "项目元数据中的直接声明",
            "path": fact.path, "sha256": sha, "startByte": fact.start_byte,
            "endByte": fact.end_byte, "method": fact.claim_mode}


def _construct_evidence(root: Path, construct: SourceConstruct, *, description: str) -> dict:
    path = Path(construct.path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"源码构造路径越出项目范围：{construct.path}")
    source = (root / path).read_bytes()
    if (construct.start_byte < 0 or construct.end_byte < construct.start_byte
            or construct.end_byte > len(source)):
        raise ValueError(f"源码构造跨度无效：{construct.path}:{construct.start_byte}-{construct.end_byte}")
    sha = hashlib.sha256(source).hexdigest()
    if sha != construct.source_sha256:
        raise ValueError(f"源码在扫描后发生变化：{construct.path}")
    evidence_id = _digest(f"{construct.construct_id}\0{sha}\0{construct.start_byte}\0{construct.end_byte}"
                          f"\0{construct.parser_id}\0{construct.parser_version}\0{description}")
    return {"evidenceId": evidence_id, "source": "input", "description": description,
            "path": construct.path, "sha256": sha, "startByte": construct.start_byte,
            "endByte": construct.end_byte, "method": construct.parser_id,
            "toolName": construct.parser_id, "toolVersion": construct.parser_version}


def _markdown_candidates(root: Path, scan: ProjectScan, candidates: list[dict], evidence: dict,
                          relations: list[dict], diagnostics: list[dict],
                          project_candidate_id: str | None) -> None:
    module_count = 0
    capability_count = 0
    paths = [Path(item.path) for item in scan.inventory
             if item.kind == "file" and item.state == "readable" and Path(item.path).suffix.lower() == ".md"]
    for relative in sorted(paths):
        source_path = root / relative
        if source_path.is_symlink():
            continue
        try:
            raw = source_path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        byte_offset = 0
        active_kind = None
        active_level = 0
        for line in text.splitlines(keepends=True):
            heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*(?:\r?\n)?$", line)
            if heading:
                level = len(heading.group(1))
                title = heading.group(2).strip().rstrip(":").casefold()
                active_kind = ("Module" if title in _MODULE_HEADINGS else
                               "Capability" if title in _CAPABILITY_HEADINGS else None)
                active_level = level
            elif line.lstrip().startswith("#"):
                active_kind = None
            elif active_kind and line.strip() and not line.lstrip().startswith(("<!--", "```")):
                bullet = re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+?)\s*(?:\r?\n)?$", line)
                if bullet:
                    label = bullet.group(1).strip()
                    name, separator, description = label.partition(":")
                    name = name.strip().strip("`*_")
                    if not name:
                        byte_offset += len(line.encode("utf-8"))
                        continue
                    line_bytes = line.encode("utf-8")
                    start = byte_offset
                    end = start + len(line_bytes.rstrip(b"\r\n"))
                    content_digest = hashlib.sha256(raw).hexdigest()
                    evidence_id = _digest(f"{relative.as_posix()}\0{start}\0{end}\0{content_digest}")
                    evidence[evidence_id] = {"evidenceId": evidence_id, "source": "documentation",
                        "description": "项目说明文档在模块/能力章节中的直接陈述",
                        "path": relative.as_posix(), "sha256": content_digest,
                        "startByte": start, "endByte": end, "method": "markdown-heading-list"}
                    candidate_id = _digest(f"candidate\0{active_kind}\0{evidence_id}")
                    candidate = {"candidateId": candidate_id, "kind": active_kind, "name": name,
                        "description": description.strip() if separator else "",
                        "epistemicStatus": "provisional", "evidenceIds": [evidence_id],
                        "sourceConstructIds": [], "attributes": [],
                        "uncertainties": ["文档陈述尚未由其他证据交叉核对。"]}
                    candidates.append(candidate)
                    if active_kind == "Module":
                        module_count += 1
                    else:
                        capability_count += 1
                    if project_candidate_id:
                        relations.append({"predicate": "defines", "subjectCandidateId": project_candidate_id,
                            "targetCandidateId": candidate_id, "epistemicStatus": "provisional",
                            "evidenceIds": [evidence_id]})
            byte_offset += len(line.encode("utf-8"))
    if module_count == 0:
        evidence_id = _digest(f"gap\0Module\0{scan.source_digest}")
        evidence[evidence_id] = {"evidenceId": evidence_id, "source": "analysis", "description":
            "已检查项目 Markdown 文件，但未发现可作为语义模块候选的明确模块章节。"}
        diagnostics.append({"code": "SEMANTIC_BOUNDARY_UNRESOLVED", "candidateKind": "Module",
                            "reason": "缺少明确的模块职责证据，不从目录或源码模块自动生成语义模块。",
                            "evidenceId": evidence_id})
    if capability_count == 0:
        evidence_id = _digest(f"gap\0Capability\0{scan.source_digest}")
        evidence[evidence_id] = {"evidenceId": evidence_id, "source": "analysis", "description":
            "已检查项目 Markdown 文件，但未发现可作为能力候选的明确功能章节。"}
        diagnostics.append({"code": "SEMANTIC_BOUNDARY_UNRESOLVED", "candidateKind": "Capability",
                            "reason": "缺少明确的能力证据，不从函数名称自动生成项目能力。",
                            "evidenceId": evidence_id})


def construct_semantic_entity_candidates(root: Path, scan: ProjectScan | None = None) -> dict:
    """Create provisional semantic candidates with source, documentation and type evidence.

    Candidate IDs identify only this construction result. Persistent EntityIds are
    assigned later by the semantic entity registry; syntax kinds never become entity IDs.
    """
    root = root.resolve(strict=True)
    scan = scan or scan_project(root)
    if Path(scan.root).resolve(strict=True) != root:
        raise ValueError("项目扫描结果与候选构造根目录不一致")
    if source_fingerprint(root) != scan.source_digest:
        raise ValueError("项目源码在扫描后发生变化；请重新扫描后再构造语义候选")

    constructs = [construct for parsed in scan.files for construct in parsed.constructs]
    evidence: dict[str, dict] = {}
    candidates: list[dict] = []
    mappings: list[dict] = []
    relation_candidates: list[dict] = []

    project_fact = next((fact for fact in scan.project_facts if fact.kind == "project_name"), None)
    project_candidate_id = None
    if project_fact is not None:
        record = _fact_evidence(root, project_fact)
        evidence[record["evidenceId"]] = record
        project_candidate_id = _digest(f"candidate\0Project\0{project_fact.id}")
        candidates.append({"candidateId": project_candidate_id, "kind": "Project", "name": project_fact.name,
            "description": "由项目清单直接声明的项目名称候选。", "epistemicStatus": "provisional",
            "evidenceIds": [record["evidenceId"]], "sourceConstructIds": [], "attributes": [],
            "uncertainties": ["名称声明不证明项目业务目的或能力边界。"]})
    else:
        evidence_id = _digest(f"gap\0Project\0{scan.source_digest}")
        evidence[evidence_id] = {"evidenceId": evidence_id, "source": "analysis",
            "description": "项目清单未提供可定位的项目名称声明。"}

    constructs_by_parent: dict[str, list[SourceConstruct]] = {}
    for construct in constructs:
        if construct.parent_id:
            constructs_by_parent.setdefault(construct.parent_id, []).append(construct)
    enum_values: dict[str, tuple[list[str], list[str]]] = {}
    computation_candidates_by_name: dict[str, list[dict]] = {}
    diagnostics: list[dict] = []
    for construct in constructs:
        if construct.syntax_kind == "enum_declaration":
            variants = [item for item in constructs_by_parent.get(construct.construct_id, [])
                        if item.syntax_kind == "enum_variant"]
            value_ids = []
            for variant in variants:
                record = _construct_evidence(root, variant, description="枚举成员源码声明")
                evidence[record["evidenceId"]] = record
                value_ids.append(record["evidenceId"])
            enum_values[construct.name] = ([item.name for item in variants], value_ids)

    for construct in constructs:
        if construct.opaque:
            continue
        if construct.syntax_kind in {"class_declaration", "struct_declaration"}:
            fields = [item for item in constructs_by_parent.get(construct.construct_id, [])
                      if item.syntax_kind == "field_declaration"]
            if not fields:
                continue
            class_evidence = _construct_evidence(root, construct, description="可能表达数据概念的类型声明")
            evidence[class_evidence["evidenceId"]] = class_evidence
            attributes = []
            attribute_evidence_ids = []
            for field in fields:
                field_evidence = _construct_evidence(root, field, description="数据类型成员源码声明")
                evidence[field_evidence["evidenceId"]] = field_evidence
                attribute_evidence_ids.append(field_evidence["evidenceId"])
                implementation_type = _field_implementation_type(field)
                enum_name = implementation_type.rsplit("::", 1)[-1].rsplit(".", 1)[-1] if implementation_type else None
                values, range_evidence = enum_values.get(enum_name, ([], []))
                value_range = ({"kind": "finite_set", "values": values,
                                "evidenceIds": range_evidence} if values and range_evidence
                               else {"kind": "unknown"})
                attributes.append({"attributeId": _digest(f"{construct.construct_id}\0{field.construct_id}"),
                    "name": field.name, "semanticType": "unknown", "implementationType": implementation_type,
                    "valueRange": value_range, "cardinality": "one", "constraints": [],
                    "evidenceIds": [field_evidence["evidenceId"]], "claimStatus": "provisional"})
            candidate_id = _digest(f"candidate\0DataEntity\0{construct.construct_id}")
            candidates.append({"candidateId": candidate_id, "kind": "DataEntity", "name": construct.name,
                "description": "由有字段的类/结构体形状提出的数据概念候选，业务含义尚未确认。",
                "epistemicStatus": "provisional",
                "evidenceIds": [class_evidence["evidenceId"], *attribute_evidence_ids],
                "sourceConstructIds": [construct.construct_id, *(field.construct_id for field in fields)],
                "attributes": attributes,
                "uncertainties": ["源码成员名称和类型是实现证据，不能单独证明业务含义。"]})
            mappings.extend({"candidateId": candidate_id, "sourceConstructId": item.construct_id,
                             "role": "represents" if item == construct else "declares"}
                            for item in [construct, *fields])
        elif construct.syntax_kind == "function_declaration":
            record = _construct_evidence(root, construct, description="可调用源码声明")
            evidence[record["evidenceId"]] = record
            candidate_id = _digest(f"candidate\0ComputationEntity\0{construct.construct_id}")
            candidates.append({"candidateId": candidate_id, "kind": "ComputationEntity",
                "name": construct.name, "description": "由可调用源码声明提出的计算职责候选，业务目的尚未确认。",
                "epistemicStatus": "provisional", "evidenceIds": [record["evidenceId"]],
                "sourceConstructIds": [construct.construct_id], "attributes": [],
                "uncertainties": ["函数边界和名称不等同业务能力边界。"]})
            implementation_views = []
            for parsed in scan.files:
                for fact in parsed.facts:
                    if (fact.path == construct.path and fact.owner == construct.name
                            and fact.kind in {"algorithm_step", "local_binding"}):
                        step_evidence = _fact_evidence(root, fact)
                        evidence[step_evidence["evidenceId"]] = step_evidence
                        implementation_views.append({"sourceFactId": fact.id, "kind": fact.kind,
                            "name": fact.name, "path": fact.path, "startByte": fact.start_byte,
                            "endByte": fact.end_byte, "text": fact.text,
                            "evidenceIds": [step_evidence["evidenceId"]]})
            candidates[-1]["implementationViews"] = sorted(implementation_views,
                key=lambda item: (item["path"], item["startByte"], item["sourceFactId"]))
            computation_candidates_by_name.setdefault(construct.name, []).append(candidates[-1])
            mappings.append({"candidateId": candidate_id, "sourceConstructId": construct.construct_id,
                             "role": "implements"})

    for construct in constructs:
        rust_test_attribute = (construct.language == "rust" and any(
            item.parent_id == construct.construct_id and item.syntax_kind == "attribute_application"
            and ("test" in item.text or "cfg(test)" in item.text) for item in constructs))
        if (construct.syntax_kind != "function_declaration"
                or not (construct.name.startswith("test_") or rust_test_attribute)):
            continue
        record = _construct_evidence(root, construct, description="测试函数入口及其断言/调用源码")
        evidence[record["evidenceId"]] = record
        called_names: set[str] = set()
        assertion_signals: set[str] = set()
        if construct.language == "python":
            try:
                tree = ast.parse(construct.text)
            except SyntaxError:
                tree = None
            if tree is not None:
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        called_names.add(node.func.id if isinstance(node.func, ast.Name) else
                                         node.func.attr if isinstance(node.func, ast.Attribute) else "")
                    if isinstance(node, ast.Assert):
                        assertion_signals.add("assert")
            if re.search(r"\b(?:pytest\.)?raises\s*\(", construct.text):
                assertion_signals.add("raises")
        else:
            called_names.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", construct.text))
            assertion_signals.update(re.findall(r"\b(assert(?:_eq|_ne|_matches|_contains)?)!", construct.text))
        candidate_id = _digest(f"candidate\0TestEntity\0{construct.construct_id}")
        candidates.append({"candidateId": candidate_id, "kind": "TestEntity", "name": construct.name,
            "description": "由测试函数声明提出的独立测试实体候选。",
            "epistemicStatus": "provisional", "evidenceIds": [record["evidenceId"]],
            "sourceConstructIds": [construct.construct_id], "attributes": [],
            "validationSignals": sorted(assertion_signals),
            "uncertainties": ["测试源码中的调用/断言不单独证明业务主张已被完整验证。"]})
        mappings.append({"candidateId": candidate_id, "sourceConstructId": construct.construct_id,
                         "role": "test_entry"})
        matches = [item for name in called_names for item in computation_candidates_by_name.get(name, [])]
        if len({item["candidateId"] for item in matches}) == 1:
            target = matches[0]
            relation_candidates.append({"predicate": "verified_by", "subjectCandidateId": target["candidateId"],
                "targetCandidateId": candidate_id, "epistemicStatus": "provisional",
                "evidenceIds": [record["evidenceId"]]})
        else:
            diagnostics.append({"code": "TEST_TARGET_UNRESOLVED", "candidateKind": "TestEntity",
                "candidateId": candidate_id,
                "reason": "测试入口没有唯一、可由源码调用证据解析的计算实体目标。",
                "evidenceId": record["evidenceId"]})

    construct_lookup = {item.construct_id: item for item in constructs}
    candidate_for_construct = {construct_id: candidate for candidate in candidates
        if candidate["kind"] in {"DataEntity", "ComputationEntity", "TestEntity"}
        for construct_id in candidate["sourceConstructIds"]}
    enum_owners: dict[str, list[dict]] = {}
    for candidate in candidates:
        if candidate["kind"] != "DataEntity":
            continue
        for attribute in candidate["attributes"]:
            implementation_type = attribute.get("implementationType")
            if implementation_type:
                enum_owners.setdefault(implementation_type.rsplit("::", 1)[-1].rsplit(".", 1)[-1], []).append(candidate)
    implementation_kinds = {"class_declaration", "struct_declaration", "enum_declaration", "enum_variant",
        "generic_parameter", "generic_parameter_list", "import_declaration",
        "decorator_application", "attribute_application", "macro_definition", "macro_invocation",
        "lambda_expression", "closure_expression", "type_alias_declaration", "constant_declaration",
        "static_declaration", "module_declaration", "trait_declaration", "implementation_block"}
    for construct in constructs:
        if construct.opaque:
            record = _construct_evidence(root, construct, description="不透明/不可解析的源码边界")
            evidence[record["evidenceId"]] = record
            diagnostics.append({"code": "OPAQUE_SOURCE_CONSTRUCT", "candidateKind": "ImplementationReference",
                "sourceConstructId": construct.construct_id, "path": construct.path,
                "startByte": construct.start_byte, "endByte": construct.end_byte,
                "evidenceId": record["evidenceId"],
                "reason": "解析器保留了不透明语法边界；未从中推导语义实体。"})
            continue
        if construct.syntax_kind not in implementation_kinds or construct.construct_id in candidate_for_construct:
            continue
        owners = enum_owners.get(construct.name, []) if construct.syntax_kind == "enum_declaration" else []
        if construct.syntax_kind == "enum_variant" and construct.parent_id:
            parent = construct_lookup.get(construct.parent_id)
            owners = enum_owners.get(parent.name, []) if parent else []
        ancestor_id = construct.parent_id
        while not owners and ancestor_id:
            owner = candidate_for_construct.get(ancestor_id)
            if owner:
                owners = [owner]
                break
            ancestor = construct_lookup.get(ancestor_id)
            ancestor_id = ancestor.parent_id if ancestor else None
        if not owners:
            record = _construct_evidence(root, construct,
                description=f"尚未映射的实现参考源码构造：{construct.syntax_kind} {construct.name}")
            evidence[record["evidenceId"]] = record
            diagnostics.append({"code": "IMPLEMENTATION_CONSTRUCT_UNMAPPED", "candidateKind": "ImplementationReference",
                "sourceConstructId": construct.construct_id, "path": construct.path,
                "syntaxKind": construct.syntax_kind, "name": construct.name,
                "startByte": construct.start_byte, "endByte": construct.end_byte,
                "evidenceId": record["evidenceId"],
                "reason": "此语言构造是实现参考，但没有证据将它映射到某个语义实体。"})
            continue
        record = _construct_evidence(root, construct,
            description=f"实现参考源码构造：{construct.syntax_kind} {construct.name}")
        evidence[record["evidenceId"]] = record
        for owner in owners:
            if construct.construct_id not in owner["sourceConstructIds"]:
                owner["sourceConstructIds"].append(construct.construct_id)
            if record["evidenceId"] not in owner["evidenceIds"]:
                owner["evidenceIds"].append(record["evidenceId"])
            mappings.append({"candidateId": owner["candidateId"],
                "sourceConstructId": construct.construct_id, "role": "implementation_reference"})

    _markdown_candidates(root, scan, candidates, evidence, relation_candidates, diagnostics,
                         project_candidate_id)
    if project_candidate_id:
        existing_pairs = {(item["subjectCandidateId"], item["targetCandidateId"])
                          for item in relation_candidates if item["predicate"] == "defines"}
        for candidate in candidates:
            pair = (project_candidate_id, candidate["candidateId"])
            if candidate["kind"] != "Project" and pair not in existing_pairs:
                relation_candidates.append({"predicate": "defines", "subjectCandidateId": pair[0],
                    "targetCandidateId": pair[1], "epistemicStatus": "provisional",
                    "evidenceIds": candidate["evidenceIds"]})
    if source_fingerprint(root) != scan.source_digest:
        raise ValueError("项目源码在候选构造期间发生变化；请重新扫描后再构造语义候选")
    return {"sourceDigest": scan.source_digest, "candidates": candidates,
            "evidence": list(evidence.values()), "sourceMappings": mappings,
            "relationCandidates": relation_candidates, "diagnostics": diagnostics}


def add_workspace_observations(root: Path, store, model: dict, facts: tuple[Fact, ...], gap: str | None,
                               input_fingerprint: str, analyzer_version: str) -> list[dict]:
    """Attach directly observed E1 Cargo membership to Project without inventing package entities."""
    projects = [item for item in model["entities"] if item["ref"]["kind"] == "Project"]
    if len(projects) > 1:
        raise ValueError("workspace metadata requires one registered Project entity")
    diagnostics = []
    if not projects:
        manifest = root / "Cargo.toml"
        if not manifest.is_file() or manifest.is_symlink():
            raise ValueError("workspace metadata requires a safe Cargo.toml at the project root")
        source = manifest.read_bytes()
        source_digest = hashlib.sha256(source).hexdigest()
        evidence_id = _digest(f"workspace-project\0{manifest}\0{source_digest}")
        evidence_by_manifest = {"evidenceId": evidence_id, "source": "input",
            "description": "虚拟Cargo workspace根目录清单；项目实体名称暂以目录名代称。",
            "path": "Cargo.toml", "sha256": source_digest, "startByte": 0, "endByte": len(source),
            "method": "cargo-workspace-manifest"}
        store.register(model["scopeId"], f"workspace-project:{model['scopeId']}", "Project", root.name,
                       [evidence_id])
        project_ref = store.lookup(model["scopeId"], f"workspace-project:{model['scopeId']}")["ref"]
        project = {"ref": project_ref, "name": root.name, "aliases": [],
            "description": "由虚拟Cargo workspace根目录提出的Project候选；项目产品名称尚未取得。",
            "attributes": [], "sourceKeys": [f"workspace-project:{model['scopeId']}"],
            "observationViews": ["E0", "E1"]}
        model["entities"].append(project)
        model["evidence"].append(evidence_by_manifest)
        model["claims"].append({"claimId": _digest(f"workspace-project-status\0{project_ref['identity']['localId']}"),
            "subject": project_ref, "predicate": "epistemicStatus", "value": "provisional",
            "evidenceIds": [evidence_id], "claimStatus": "provisional"})
        model["coverage"].append({"coverageId": _digest(
            f"workspace-project-coverage\0{input_fingerprint}\0{analyzer_version}"),
            "entity": project_ref, "selector": "project", "status": "obtained",
            "inputFingerprint": input_fingerprint, "analyzerVersion": analyzer_version,
            "presentationStatus": "included", "freshness": "current"})
        projects = [project]
        diagnostics.append({"code": "VIRTUAL_WORKSPACE_PROJECT_PROVISIONAL", "severity": "gap",
            "reason": "Cargo虚拟workspace没有根package；以目录名临时代称Project，未取得产品名称。",
            "entityRef": project_ref})
    project = projects[0]
    project["observationViews"] = sorted(set(project["observationViews"]) | {"E1"})
    evidence_by_id = {item["evidenceId"]: item for item in model["evidence"]}
    claims_by_id = {item["claimId"]: item for item in model["claims"]}
    for fact in facts:
        evidence = _fact_evidence(root, fact)
        evidence["evidenceId"] = _digest(f"cargo-metadata\0{fact.name}\0{fact.owner or ''}\0{evidence['sha256']}")
        evidence.update({"source": "cargo_metadata", "description": "Cargo metadata确认的workspace package成员",
                         "method": "cargo metadata --no-deps --offline", "toolName": "cargo"})
        evidence_by_id[evidence["evidenceId"]] = evidence
        claim_id = _digest(f"claim\0{project['ref']['identity']['localId']}\0workspaceMemberPackage\0"
                           f"{fact.name}\0{fact.owner or ''}")
        claim = claims_by_id.get(claim_id)
        if claim is None:
            claim = {"claimId": claim_id, "subject": project["ref"],
                     "predicate": "workspaceMemberPackage",
                     "value": {"packageName": fact.name, "manifestPath": fact.owner or "Cargo.toml"},
                     "evidenceIds": [], "claimStatus": "confirmed"}
            claims_by_id[claim_id] = claim
        claim["evidenceIds"] = sorted(set(claim["evidenceIds"]) | {evidence["evidenceId"]})

    coverage_status = "not_acquired" if gap else "obtained"
    coverage_id = _digest(f"workspace-coverage\0{project['ref']['identity']['localId']}\0"
                          f"{input_fingerprint}\0{analyzer_version}\0{coverage_status}")
    if not any(item["coverageId"] == coverage_id for item in model["coverage"]):
        model["coverage"].append({"coverageId": coverage_id, "entity": project["ref"],
            "selector": "workspace-members", "status": coverage_status,
            "inputFingerprint": input_fingerprint, "analyzerVersion": analyzer_version,
            "presentationStatus": "included", "freshness": "current"})
    if gap:
        diagnostics.append({"code": "WORKSPACE_METADATA_NOT_ACQUIRED", "severity": "gap",
                            "reason": gap, "entityRef": project["ref"]})
    model["evidence"] = list(evidence_by_id.values())
    model["claims"] = list(claims_by_id.values())
    return diagnostics


def _field_implementation_type(field: SourceConstruct) -> str | None:
    if field.declared_type:
        return field.declared_type.strip() or None
    text = field.text.strip()
    match = re.match(r"[^:]+:\s*([^=;,\n]+)", text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def construct_and_query_semantic_entities(root: Path, store, selector: str = "project") -> dict:
    """Construct/persist provisional candidates on a miss, then query the durable archive."""
    from .semantic_entity_query import query_entity_store

    root = root.resolve(strict=True)
    store.validate_root(root)
    profile_digest = analysis_profile_digest()
    current_source = source_fingerprint(root)
    input_fingerprint = "sha256:" + _digest(f"{current_source}\0{profile_digest}")
    scope_id = "project:" + _digest(str(root))
    existing = store.read(scope_id)
    if existing and any(item["selector"] == "all-entities"
                        and item["inputFingerprint"] == input_fingerprint
                        and item["analyzerVersion"] == profile_digest
                        for item in existing["coverage"]):
        result = query_entity_store(store, {"version": "1.0.0", "profile": "semantic-entity-query-1",
            "scopeId": scope_id, "selector": selector, "inputFingerprint": input_fingerprint,
            "analyzerVersion": profile_digest})
        result["constructionStatus"] = "reused"
        result["constructionDiagnostics"] = store.read_diagnostics(scope_id, input_fingerprint)
        return result

    scan = scan_project(root)
    constructed = construct_semantic_entity_candidates(root, scan)
    prior_registry = store.registered_entities(scope_id)
    refs: dict[str, dict] = {}
    records = {item["evidenceId"]: item for item in constructed["evidence"]}
    entities = []
    claims = []
    coverage = []
    observations = {"Project": "E0", "Module": "E1", "Capability": "E1", "DataEntity": "E2",
                    "ComputationEntity": "E2", "ExternalActor": "E3", "TestEntity": "E4"}
    for candidate in constructed["candidates"]:
        source_key = f"candidate:{candidate['kind']}:{candidate['candidateId']}"
        registration = store.register(scope_id, source_key, candidate["kind"], candidate["name"],
            candidate["evidenceIds"], continuity_from=[item for item in prior_registry
                if item["name"] == candidate["name"] and item["ref"]["kind"] == candidate["kind"]])
        ref = registration["ref"]
        refs[candidate["candidateId"]] = ref
        source_keys = sorted(set(candidate.get("sourceConstructIds", [])) | {source_key})
        entity = {"ref": ref, "name": candidate["name"], "aliases": [],
            "description": candidate["description"], "attributes": candidate.get("attributes", []),
            "sourceKeys": source_keys, "observationViews": [observations[candidate["kind"]]]}
        for attr in entity["attributes"]:
            attr["claimStatus"] = "provisional"
            if attr.get("implementationType") is None:
                attr.pop("implementationType", None)
        entities.append(entity)
        status_id = _digest(f"claim\0{candidate['candidateId']}\0epistemicStatus")
        claims.append({"claimId": status_id, "subject": ref, "predicate": "epistemicStatus",
            "value": candidate["epistemicStatus"], "evidenceIds": candidate["evidenceIds"],
            "claimStatus": "provisional"})
        coverage_id = _digest(f"coverage\0{candidate['candidateId']}\0{input_fingerprint}\0{profile_digest}")
        coverage.append({"coverageId": coverage_id, "entity": ref, "selector": "all-entities",
            "status": "obtained", "inputFingerprint": input_fingerprint,
            "analyzerVersion": profile_digest, "presentationStatus": "not_expanded", "freshness": "current"})
    relations = []
    for index, candidate in enumerate(constructed["relationCandidates"]):
        subject = refs.get(candidate["subjectCandidateId"])
        target = refs.get(candidate["targetCandidateId"])
        if subject is None or target is None:
            continue
        relations.append({"relationId": _digest(f"relation\0{index}\0{candidate['predicate']}\0"
            f"{candidate['subjectCandidateId']}\0{candidate['targetCandidateId']}"),
            "predicate": candidate["predicate"], "subject": subject, "target": target,
            "evidenceIds": candidate["evidenceIds"], "condition": {"kind": "true"},
            "claimStatus": "provisional"})
    construct_by_id = {item.construct_id: item for parsed in scan.files for item in parsed.constructs}
    evidence_by_location: dict[tuple[str, int, int], list[str]] = {}
    for item in records.values():
        if "path" in item:
            evidence_by_location.setdefault((item["path"], item["startByte"], item["endByte"]), []).append(
                item["evidenceId"])
    source_mappings = []
    mapped_constructs = set()
    for mapping in constructed["sourceMappings"]:
        construct = construct_by_id.get(mapping["sourceConstructId"])
        target = refs.get(mapping["candidateId"])
        if construct is None or target is None:
            continue
        mapped_constructs.add(construct.construct_id)
        source_mapping = {"mappingId": _digest(f"mapping\0{mapping['candidateId']}\0"
            f"{construct.construct_id}\0{construct.source_sha256}\0{mapping['role']}"), "target": target,
            "sourceConstruct": {"constructId": construct.construct_id, "sourceKey": construct.source_key,
                "language": construct.language, "syntaxKind": construct.syntax_kind, "name": construct.name,
                "path": construct.path, "sha256": construct.source_sha256,
                "startByte": construct.start_byte, "endByte": construct.end_byte,
                "parentConstructId": construct.parent_id, "parserId": construct.parser_id,
                "parserVersion": construct.parser_version, "opaque": construct.opaque,
                "text": construct.text, **({"declaredType": construct.declared_type}
                                             if construct.declared_type is not None else {})},
            "role": mapping["role"], "mappingStatus": "mapped",
            "evidenceIds": sorted(evidence_by_location.get(
                (construct.path, construct.start_byte, construct.end_byte), []))}
        source_mappings.append(source_mapping)
    for diagnostic in constructed["diagnostics"]:
        construct = construct_by_id.get(diagnostic.get("sourceConstructId"))
        if construct is None or construct.construct_id in mapped_constructs:
            continue
        source_mappings.append({"mappingId": _digest(f"unresolved\0{construct.construct_id}\0{construct.source_sha256}"),
            "sourceConstruct": {"constructId": construct.construct_id, "sourceKey": construct.source_key,
                "language": construct.language, "syntaxKind": construct.syntax_kind, "name": construct.name,
                "path": construct.path, "sha256": construct.source_sha256,
                "startByte": construct.start_byte, "endByte": construct.end_byte,
                "parentConstructId": construct.parent_id, "parserId": construct.parser_id,
                "parserVersion": construct.parser_version, "opaque": construct.opaque,
                "text": construct.text, **({"declaredType": construct.declared_type}
                                             if construct.declared_type is not None else {})},
            "role": "implementation_reference", "mappingStatus": "unresolved",
            "evidenceIds": [diagnostic["evidenceId"]]})
    for candidate in constructed["candidates"]:
        target = refs[candidate["candidateId"]]
        parent = next((construct_by_id[item] for item in candidate["sourceConstructIds"]
                       if item in construct_by_id), None)
        if parent is None:
            continue
        for view in candidate.get("implementationViews", []):
            parsed = next((item for item in scan.files if item.path == view["path"]), None)
            if parsed is None:
                continue
            source_construct = {"constructId": view["sourceFactId"], "sourceKey": view["sourceFactId"],
                "language": parsed.language, "syntaxKind": view["kind"], "name": view["name"],
                "path": view["path"], "sha256": parsed.source_sha256,
                "startByte": view["startByte"], "endByte": view["endByte"],
                "parentConstructId": parent.construct_id, "parserId": parent.parser_id,
                "parserVersion": parent.parser_version, "opaque": False, "text": view["text"]}
            source_mappings.append({"mappingId": _digest(f"algorithm-view\0{candidate['candidateId']}\0"
                f"{view['sourceFactId']}\0{parsed.source_sha256}"), "target": target,
                "sourceConstruct": source_construct, "role": "algorithm_view", "mappingStatus": "mapped",
                "evidenceIds": view["evidenceIds"]})
    continuity = []
    for registration in store.continuity_candidates(scope_id):
        if registration["current"] in refs.values():
            continuity.append(registration)
    prior_evidence = {item["evidenceId"]: item for item in (existing or {}).get("evidence", [])}
    continuity_evidence_ids = {item for candidate in continuity for item in candidate.get("evidenceIds", [])}
    for evidence_id in continuity_evidence_ids - records.keys():
        if evidence_id in prior_evidence:
            records[evidence_id] = prior_evidence[evidence_id]
    document = {"version": "1.0.0", "profile": "semantic-entity-model-1", "scopeId": scope_id,
        "entities": entities, "claims": claims, "relations": relations,
        "continuityCandidates": continuity, "sourceMappings": source_mappings,
        "evidence": list(records.values()), "coverage": coverage}
    store.write(document, constructed["diagnostics"])
    result = query_entity_store(store, {"version": "1.0.0", "profile": "semantic-entity-query-1",
        "scopeId": scope_id, "selector": selector, "inputFingerprint": input_fingerprint,
        "analyzerVersion": profile_digest})
    result["constructionStatus"] = "constructed"
    result["constructionDiagnostics"] = constructed["diagnostics"]
    return result
