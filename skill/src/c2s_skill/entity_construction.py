"""证据驱动的语义实体候选构造；候选身份尚不是持久实体身份。"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

from .acquisition import Fact, ProjectScan, SourceConstruct, scan_project
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
    evidence_id = _digest(f"{construct.construct_id}\0{sha}\0{construct.start_byte}\0{construct.end_byte}")
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

    _markdown_candidates(root, scan, candidates, evidence, relation_candidates, diagnostics,
                         project_candidate_id)
    if source_fingerprint(root) != scan.source_digest:
        raise ValueError("项目源码在候选构造期间发生变化；请重新扫描后再构造语义候选")
    return {"sourceDigest": scan.source_digest, "candidates": candidates,
            "evidence": list(evidence.values()), "sourceMappings": mappings,
            "relationCandidates": relation_candidates, "diagnostics": diagnostics}


def _field_implementation_type(field: SourceConstruct) -> str | None:
    if field.declared_type:
        return field.declared_type.strip() or None
    text = field.text.strip()
    match = re.match(r"[^:]+:\s*([^=;,\n]+)", text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None
