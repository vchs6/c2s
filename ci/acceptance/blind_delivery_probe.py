#!/usr/bin/env python3
"""Fixed public synthetic two-way repository and delivery diagnostic.

No model, private suite, arbitrary candidate, or AI role broker is launched.
The trusted host owns both disposable public fixtures. Only the selected role
repository is visible to the constrained worker; local controls alone prove no
permission boundary. This never opens the product development gate.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


SOURCE = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boundary = load_module("public_role_boundary", SOURCE / "ci/acceptance/role_repository_probe.py")
preparation = load_module("public_role_preparation", SOURCE / "scripts/prepare_role_repositories.py")
CANDIDATE = "PUBLIC_SYNTHETIC_CANDIDATE.py"
SUITE = "PUBLIC_SYNTHETIC_SUITE.json"
CANDIDATE_MARKER = "PUBLIC_SYNTHETIC_CANDIDATE_CONTENT"
SUITE_MARKER = "PUBLIC_SYNTHETIC_SUITE_CONTENT"
CANDIDATE_BYTES = (
    '# PUBLIC_SYNTHETIC_CANDIDATE_CONTENT\n'
    'import json, sys\n'
    'print(json.dumps({"answer": sum(map(int, sys.argv[1:])), '
    '"diagnostic": "PUBLIC_SYNTHETIC_RAW_DIAGNOSTIC"}))\n'
).encode()
SUITE_BYTES = (json.dumps({"marker": SUITE_MARKER, "inputs": [19, 23],
                          "expected_answer": 42}, sort_keys=True) + "\n").encode()
EXTRA_CHECKS = ("own_delivery_input", "opposite_content_absent", "opposite_delivery_reads_denied")

# Extend the existing fixed worker, preserving its filesystem/resource checks.
# Scan loose Git objects as well as working files, so deleted fixture content
# cannot hide in the role's fresh snapshot history. No Git executable is needed.
EXTRA_WORKER = r'''
checks["own_delivery_input"] = False
checks["opposite_content_absent"] = False
checks["opposite_delivery_reads_denied"] = False
try:
    import zlib
    own = ("PUBLIC_SYNTHETIC_CANDIDATE.py" if role == "coding"
           else "PUBLIC_SYNTHETIC_SUITE.json")
    forbidden = (b"PUBLIC_SYNTHETIC_SUITE_CONTENT" if role == "coding"
                 else b"PUBLIC_SYNTHETIC_CANDIDATE_CONTENT")
    other = "author" if role == "coding" else "coding"
    opposite_files = (["PUBLIC_SYNTHETIC_SUITE.json"] if role == "coding" else
                      ["PUBLIC_SYNTHETIC_CANDIDATE.py", "scripts/check_public_environment.py"])
    checks["opposite_delivery_reads_denied"] = all(
        denied_read(prefix + "/" + filename)
        for prefix in ("../" + other, "/" + other, host_root + "/" + other)
        for filename in opposite_files)
    checks["own_delivery_input"] = pathlib.Path(own).is_file() and (
        pathlib.Path("scripts/check_public_environment.py").is_file() if role == "coding"
        else json.loads(pathlib.Path(own).read_text())["marker"] ==
             "PUBLIC_SYNTHETIC_SUITE_CONTENT")
    objects = pathlib.Path(".git/objects")
    checks["opposite_content_absent"] = (
        not pathlib.Path("PUBLIC_SYNTHETIC_SUITE.json" if role == "coding"
                         else "PUBLIC_SYNTHETIC_CANDIDATE.py").exists() and
        (role == "coding" or not pathlib.Path("scripts/check_public_environment.py").exists()) and
        all(forbidden not in path.read_bytes() for path in pathlib.Path(".").rglob("*")
            if path.is_file() and ".git" not in path.parts) and
        all(forbidden not in zlib.decompress(path.read_bytes())
            for path in objects.glob("??/*") if path.is_file()) and
        not any((objects / "pack").iterdir()) and
        not (objects / "info/alternates").exists())
except Exception:
    pass
'''
WORKER = boundary.PROBE_SETUP + EXTRA_WORKER + boundary.PROBE_RESULT


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def binding(root: Path, commit: str) -> dict:
    environment = json.dumps({"python": sys.version, "platform": sys.platform,
                              "executor": "fixed-public-synthetic-host-v1"}, sort_keys=True)
    return {"source_commit": commit,
            "candidate_sha256": digest((root / "coding" / CANDIDATE).read_bytes()),
            "suite_sha256": digest((root / "author" / SUITE).read_bytes()),
            "contract_sha256": {
                role: {path: digest((root / role / path).read_bytes())
                       for path in boundary.CONTRACTS}
                for role in ("coding", "author")},
            "environment_sha256": digest(environment.encode())}


def acceptance(root: Path, commit: str, expected: dict, submitted: dict) -> dict:
    """Return an allowlisted summary; reject stale binding before execution."""
    report = {"synthetic_only": True, "model_invoked": False,
              "development_ready": False, "status": "binding_mismatch"}
    current = binding(root, commit)
    if (submitted != expected or expected != current or
            current["contract_sha256"]["coding"] != current["contract_sha256"]["author"]):
        return report
    suite = json.loads((root / "author" / SUITE).read_bytes())
    result = boundary.run(
        [sys.executable, "-I", "-B", str(root / "coding" / CANDIDATE),
         *[str(value) for value in suite["inputs"]]], timeout=20, category="synthetic_candidate")
    value = boundary.parse_json(result.stdout, "synthetic_candidate")
    passed = (result.returncode == 0 and isinstance(value, dict) and
              set(value) == {"answer", "diagnostic"} and
              type(value["answer"]) is int and value["answer"] == suite["expected_answer"])
    report["status"] = "synthetic_acceptance_passed" if passed else "synthetic_acceptance_failed"
    return report


def inspect_repository(root: Path, role: str, git: str) -> bool:
    repository = root / role
    objects = preparation.run_git(git, repository, "rev-list", "--objects", "--all").splitlines()
    forbidden = SUITE_MARKER.encode() if role == "coding" else CANDIDATE_MARKER.encode()
    for entry in objects:
        oid = entry.split(b" ", 1)[0].decode("ascii")
        if forbidden in preparation.run_git(git, repository, "cat-file", "-p", oid):
            return False
    history = preparation.run_git(git, repository, "rev-list", "--all", "--count").strip()
    return (history == b"1" and not preparation.run_git(git, repository, "remote").strip()
            and not (repository / ".git/objects/info/alternates").exists()
            and not (repository / (SUITE if role == "coding" else CANDIDATE)).exists()
            and (role == "coding" or not (repository / boundary.CANDIDATE).exists()))


def configure(root: Path, commit: str, git: str, report: dict) -> None:
    # Both fixtures are fixed public infrastructure, not c2s product tests.
    (root / "coding" / CANDIDATE).write_bytes(CANDIDATE_BYTES)
    (root / "author" / SUITE).write_bytes(SUITE_BYTES)
    for role, filename in (("coding", CANDIDATE), ("author", SUITE)):
        preparation.run_git(git, root / role, "add", "--", filename)
        preparation.run_git(git, root / role, "commit", "--quiet", "--amend",
                            "--no-edit", "--no-verify", "--no-gpg-sign")
    controls = {
        "coding_own_candidate": (root / "coding" / CANDIDATE).read_bytes() == CANDIDATE_BYTES,
        "author_own_suite": (root / "author" / SUITE).read_bytes() == SUITE_BYTES,
        "coding_no_suite_or_history": inspect_repository(root, "coding", git),
        "author_no_candidate_or_history": inspect_repository(root, "author", git),
    }
    report["preparation_checks"] = controls
    if not all(controls.values()):
        raise boundary.ProbeError("blind_preparation_failed")
    expected = binding(root, commit)
    report["delivery_binding"] = expected
    # MANIFEST/ROLE_INPUT remain evidence for the original prepared snapshot.
    # This separate manifest binds the amended fixture heads and final content;
    # do not represent the original role_commit fields as current delivery heads.
    final_heads = {role: boundary.git_head(git, root / role) for role in ("coding", "author")}
    delivery_manifest = {"format": 1, "scope": "public-synthetic-delivery-only",
                         "synthetic_only": True, "model_invoked": False,
                         "development_ready": False, "binding": expected,
                         "final_role_commits": final_heads,
                         "initial_preparation_manifest_scope": "pre-fixture-snapshot-only"}
    preparation.write_json(root / "DELIVERY_MANIFEST.json", delivery_manifest)
    report["delivery_manifest"] = delivery_manifest
    accepted = acceptance(root, commit, expected, dict(expected))
    mismatches = []
    for key in expected:
        changed = dict(expected)
        changed[key] = "0" * len(expected[key])
        mismatches.append(acceptance(root, commit, expected, changed))
    contract = root / "author" / boundary.CONTRACTS[0]
    original_contract = contract.read_bytes()
    try:
        contract.write_bytes(original_contract + b"\nPUBLIC SYNTHETIC CONTRACT DRIFT\n")
        drifted = acceptance(root, commit, expected, dict(expected))
    finally:
        contract.write_bytes(original_contract)
    # Rebind a deliberately wrong public synthetic candidate; the suite must
    # reject behavior too, rather than merely reporting a hash comparison.
    candidate = root / "coding" / CANDIDATE
    try:
        candidate.write_bytes(CANDIDATE_BYTES.replace(b"sum(map(int, sys.argv[1:]))", b"41"))
        wrong_binding = binding(root, commit)
        wrong = acceptance(root, commit, wrong_binding, dict(wrong_binding))
    finally:
        candidate.write_bytes(CANDIDATE_BYTES)
    summaries = [accepted, wrong, drifted, *mismatches]
    allowed = {"synthetic_only", "model_invoked", "development_ready", "status"}
    checks = {
        "matching_binding_passed": accepted["status"] == "synthetic_acceptance_passed",
        "wrong_answer_rejected": wrong["status"] == "synthetic_acceptance_failed",
        "contract_drift_rejected": drifted["status"] == "binding_mismatch",
        "all_binding_mismatches_rejected": all(item["status"] == "binding_mismatch" for item in mismatches),
        "controlled_report_only": all(set(item) == allowed for item in summaries),
    }
    report["acceptance_checks"] = checks
    if not all(checks.values()):
        raise boundary.ProbeError("synthetic_acceptance_controls_failed")


def local_controls(report: dict) -> None:
    git = shutil.which("git", path=boundary.HOST_ENV["PATH"])
    if git is None:
        raise boundary.ProbeError("git_unavailable")
    commit = boundary.git_head(git, SOURCE)
    report["source_commit"] = commit
    with tempfile.TemporaryDirectory(prefix="c2s-public-blind-controls-") as directory:
        root = Path(directory) / "repositories"
        manifest = preparation.prepare(str(SOURCE), commit, str(root))
        boundary.verify_preparation(root, commit, git, json.dumps(manifest).encode())
        configure(root, commit, git, report)
    report["status"] = "synthetic_local_controls_passed"


def main() -> int:
    report = {"format": 1, "scope": "public-synthetic-two-way-blind-diagnostic",
              "synthetic_only": True, "model_invoked": False, "development_ready": False,
              "ai_role_broker_deployed": False, "container_repo_boundary_passed": False,
              "status": "failed", "role": None, "preparation_checks": {},
              "acceptance_checks": {}}
    parser = boundary.SafeArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--role", choices=("coding", "author"))
    mode.add_argument("--local-controls", action="store_true")
    try:
        arguments = parser.parse_args()
        report["role"] = arguments.role
        if arguments.local_controls:
            local_controls(report)
        else:
            boundary.probe(
                arguments.role, report,
                prepare_check=lambda root, commit, git: configure(root, commit, git, report),
                worker_code=WORKER, worker_checks=(*boundary.CHECKS, *EXTRA_CHECKS))
    except (boundary.ProbeError, preparation.PreparationError) as error:
        report["error"] = str(error)
    except Exception:
        report["error"] = "blind_diagnostic_failure"
    if "error" in report:
        report["status"] = "failed"
        report["container_repo_boundary_passed"] = False
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] in ("synthetic_local_controls_passed", "synthetic_probe_passed") else 1


if __name__ == "__main__":
    sys.exit(main())
