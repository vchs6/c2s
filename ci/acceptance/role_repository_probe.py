#!/usr/bin/env python3
"""Trusted CI host diagnostic for public synthetic role repositories only.

This fixed probe is not a model tool broker or an arbitrary candidate launcher.
Each role runs in a separate CI job. Its worker receives one repository mount
and no host Docker interface, source token, model credential or private suite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid


ROLES = ("coding", "review", "author", "runner", "verifier")
IMAGE = "python:3.12-slim"
DIGEST = re.compile(r"python@sha256:[0-9a-f]{64}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
MARKER = "PUBLIC_SYNTHETIC_MARKER.txt"
OUTPUT = "PUBLIC_PROBE_OUTPUT.txt"
CONTRACTS = (
    "openspec/specs/independent-delivery/spec.md",
    "openspec/specs/semantic-fact-query/spec.md",
)
CANDIDATE = "scripts/check_public_environment.py"
OUTPUT_LIMIT = 16384
HOST_ENV = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "DOCKER_CONFIG": "/nonexistent",
    "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": os.devnull, "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0",
}
CHECKS = (
    "uid_gid", "legal_inputs", "legal_output_write", "relative_reads_denied",
    "absolute_reads_denied", "host_reads_denied", "relative_writes_denied",
    "absolute_writes_denied", "host_writes_denied", "docker_sockets_denied",
    "sensitive_environment_absent", "network_none", "privileges_restricted",
    "rootfs_read_only", "resource_limits",
)


# No caller-supplied program, path expansion or shell is executed in the worker.
# All attempted cross-role paths name this invocation's public synthetic files.
PROBE = r'''
import json, os, pathlib, sys

roles = ("coding", "review", "author", "runner", "verifier")
names = (
    "uid_gid", "legal_inputs", "legal_output_write", "relative_reads_denied",
    "absolute_reads_denied", "host_reads_denied", "relative_writes_denied",
    "absolute_writes_denied", "host_writes_denied", "docker_sockets_denied",
    "sensitive_environment_absent", "network_none", "privileges_restricted",
    "rootfs_read_only", "resource_limits",
)
checks = {name: False for name in names}

def denied_read(path):
    try:
        pathlib.Path(path).read_bytes()
    except (PermissionError, FileNotFoundError):
        return True
    except OSError:
        return False
    return False

def denied_write(path):
    try:
        with pathlib.Path(path).open("xb") as stream:
            stream.write(b"PUBLIC SYNTHETIC FORBIDDEN OUTPUT\n")
    except (PermissionError, FileNotFoundError):
        return True
    except OSError:
        return False
    return False

def unavailable_socket(path):
    try:
        pathlib.Path(path).lstat()
    except (PermissionError, FileNotFoundError):
        return True
    except OSError:
        return False
    return False

try:
    role, commit, uid, gid, host_root = sys.argv[1:]
    if role not in roles:
        raise ValueError()
    checks["uid_gid"] = (os.getuid() == int(uid) != 0 and
                         os.getgid() == int(gid) != 0)
    marker = ("PUBLIC SYNTHETIC MARKER\nrole=" + role + "\n"
              "Public synthetic data only; no hidden assertions or private suite.\n"
              "Role names do not enforce identity or tool permissions.\n")
    role_input = json.loads(pathlib.Path("ROLE_INPUT.json").read_text())
    checks["legal_inputs"] = (
        pathlib.Path("PUBLIC_SYNTHETIC_MARKER.txt").read_text() == marker and
        role_input.get("role") == role and
        role_input.get("source_commit") == commit and
        role_input.get("synthetic_only") is True and
        pathlib.Path(".git/HEAD").read_text() == "ref: refs/heads/main\n")
    output = pathlib.Path("PUBLIC_PROBE_OUTPUT.txt")
    expected_output = "PUBLIC SYNTHETIC PROBE OUTPUT\nrole=" + role + "\n"
    output.write_text(expected_output)
    checks["legal_output_write"] = output.read_text() == expected_output
    other_roles = [other for other in roles if other != role]
    roots = {
        "relative": ["../" + other for other in other_roles],
        "absolute": ["/" + other for other in other_roles],
        "host": [host_root + "/" + other for other in other_roles],
    }
    for kind, paths in roots.items():
        checks[kind + "_reads_denied"] = all(
            denied_read(path + "/PUBLIC_SYNTHETIC_MARKER.txt") for path in paths)
        checks[kind + "_writes_denied"] = all(
            denied_write(path + "/PUBLIC_FORBIDDEN_PROBE_OUTPUT.txt") for path in paths)
    sockets = ("/var/run/docker.sock", "/run/docker.sock",
               "/run/user/" + uid + "/docker.sock",
               "/run/containerd/containerd.sock")
    checks["docker_sockets_denied"] = all(unavailable_socket(path) for path in sockets)
    # env -i clears image variables too; CPython may add only its locale coercion.
    allowed = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_CTYPE": "C.UTF-8"}
    sensitive = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY",
                 "GITHUB", "OPENAI", "ANTHROPIC", "AZURE", "AWS_", "DOCKER")
    checks["sensitive_environment_absent"] = (
        all(key in allowed and value == allowed[key] for key, value in os.environ.items())
        and os.environ.get("PATH") == allowed["PATH"]
        and not any(part in key.upper() for key in os.environ for part in sensitive))
    checks["network_none"] = {p.name for p in pathlib.Path("/sys/class/net").iterdir()} == {"lo"}
    status = dict(line.split(":", 1) for line in
                  pathlib.Path("/proc/self/status").read_text().splitlines() if ":" in line)
    checks["privileges_restricted"] = (
        status.get("NoNewPrivs", "").strip() == "1" and
        int(status.get("CapEff", "1").strip(), 16) == 0)
    # Only our own synthetic target is used on the immutable root filesystem.
    try:
        pathlib.Path("/tmp/PUBLIC_ROOTFS_PROBE_OUTPUT.txt").write_bytes(b"PUBLIC SYNTHETIC\n")
    except OSError as error:
        import errno
        checks["rootfs_read_only"] = error.errno == errno.EROFS
    cgroup = pathlib.Path("/sys/fs/cgroup")
    cpu = (cgroup / "cpu.max").read_text().split()
    checks["resource_limits"] = (
        (cgroup / "pids.max").read_text().strip() == "32" and
        (cgroup / "memory.max").read_text().strip() == "134217728" and
        len(cpu) == 2 and cpu[0].isdigit() and cpu[1].isdigit() and
        int(cpu[0]) == int(cpu[1]))
except Exception:
    pass
passed = all(checks.values())
print(json.dumps({"status": "passed" if passed else "failed", "checks": checks}, sort_keys=True))
sys.exit(0 if passed else 1)
'''


class ProbeError(Exception):
    """Contains only a fixed, safe error category."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ProbeError("invalid_arguments")


def run(command: list[str], *, timeout: int, category: str) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            command, shell=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=HOST_ENV, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        raise ProbeError(category + "_timeout") from None
    except OSError:
        raise ProbeError(category + "_unavailable") from None
    return result


def parse_json(data: bytes, category: str) -> dict | list:
    if len(data) > OUTPUT_LIMIT:
        raise ProbeError(category + "_output_limit")
    try:
        value = json.loads(data)
    except (ValueError, UnicodeError):
        raise ProbeError(category + "_invalid_json") from None
    if not isinstance(value, (dict, list)):
        raise ProbeError(category + "_invalid_schema")
    return value


def marker_text(role: str) -> str:
    return ("PUBLIC SYNTHETIC MARKER\nrole=" + role + "\n"
            "Public synthetic data only; no hidden assertions or private suite.\n"
            "Role names do not enforce identity or tool permissions.\n")


def git_head(git: str, repository: Path) -> str:
    process = run([
        git, "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false",
        "-c", "protocol.allow=never", "-C", str(repository),
        "rev-parse", "--verify", "HEAD",
    ], timeout=20, category="git")
    if process.returncode or len(process.stdout) != 41:
        raise ProbeError("git_head_failed")
    value = process.stdout.decode("ascii").strip()
    if not SHA.fullmatch(value):
        raise ProbeError("invalid_git_head")
    return value


def snapshot(root: Path) -> dict:
    """Capture only freshly prepared public trees; reject symlinks/special files."""
    result = {}
    for role in ROLES:
        repository = root / role
        for path in (repository, *sorted(repository.rglob("*"))):
            metadata = path.lstat()
            mode = metadata.st_mode
            if stat.S_ISREG(mode):
                content = hashlib.sha256(path.read_bytes()).hexdigest()
            elif stat.S_ISDIR(mode):
                content = "directory"
            else:
                raise ProbeError("unexpected_prepared_file_type")
            result[str(path.relative_to(root))] = [stat.S_IMODE(mode), content]
    return result


def verify_preparation(root: Path, commit: str, git: str, output: bytes) -> None:
    manifest = parse_json((root / "MANIFEST.json").read_bytes(), "manifest")
    if (manifest != parse_json(output, "preparation") or
            not isinstance(manifest, dict) or manifest.get("format") != 1 or
            manifest.get("scope") != "public-role-repositories-only" or
            manifest.get("source_commit") != commit or
            manifest.get("repository_setup_passed") is not True or
            manifest.get("permission_isolation_verified") is not False or
            manifest.get("development_ready") is not False or
            not isinstance(manifest.get("roles"), dict) or
            set(manifest["roles"]) != set(ROLES)):
        raise ProbeError("manifest_mismatch")
    for role in ROLES:
        repository = root / role
        entry = manifest["roles"][role]
        expected_paths = CONTRACTS if role == "author" else (*CONTRACTS, CANDIDATE)
        if (not isinstance(entry, dict) or entry.get("path") != role or
                entry.get("role_commit") != git_head(git, repository) or
                not isinstance(entry.get("files"), list) or
                len(entry["files"]) != len(expected_paths)):
            raise ProbeError("role_manifest_mismatch")
        for file_entry, path in zip(entry["files"], expected_paths):
            if (not isinstance(file_entry, dict) or set(file_entry) != {"path", "sha256"} or
                    file_entry["path"] != path or
                    not isinstance(file_entry["sha256"], str) or
                    not HASH.fullmatch(file_entry["sha256"]) or
                    hashlib.sha256((repository / path).read_bytes()).hexdigest() != file_entry["sha256"]):
                raise ProbeError("prepared_blob_mismatch")
        expected_input = {"role": role, "source_commit": commit,
                          "files": entry["files"], "synthetic_only": True}
        if (parse_json((repository / "ROLE_INPUT.json").read_bytes(), "role_input") != expected_input or
                (repository / MARKER).read_text(encoding="utf-8") != marker_text(role)):
            raise ProbeError("host_positive_control_failed")


def probe(role: str, report: dict) -> None:
    source = Path(__file__).resolve(strict=True).parents[2]
    commit = os.environ.get("GITHUB_SHA", "")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ProbeError("trusted_ci_required")
    if not SHA.fullmatch(commit):
        raise ProbeError("invalid_github_sha")
    report["source_commit"] = commit
    git = shutil.which("git", path=HOST_ENV["PATH"])
    if git is None:
        raise ProbeError("git_unavailable")
    if git_head(git, source) != commit:
        raise ProbeError("source_commit_mismatch")
    docker = shutil.which("docker", path=HOST_ENV["PATH"])
    if docker is None:
        raise ProbeError("docker_unavailable")
    uid, gid = os.getuid(), os.getgid()
    if uid == 0 or gid == 0:
        raise ProbeError("nonroot_host_required")
    temp_value = os.environ.get("RUNNER_TEMP", "")
    if not temp_value or not Path(temp_value).is_absolute():
        raise ProbeError("invalid_runner_temp")
    temp_root = Path(temp_value).resolve(strict=True)
    if not temp_root.is_dir() or "," in str(temp_root):
        raise ProbeError("invalid_runner_temp")
    with tempfile.TemporaryDirectory(prefix="c2s-role-repository-", dir=temp_root) as directory:
        root = Path(directory) / "repositories"
        prepared = run([
            sys.executable, "-I", "-B", str(source / "scripts/prepare_role_repositories.py"),
            "--source", str(source), "--ref", commit, "--destination", str(root),
        ], timeout=120, category="preparation")
        if prepared.returncode:
            raise ProbeError("repository_preparation_failed")
        verify_preparation(root, commit, git, prepared.stdout)
        before = snapshot(root)
        report["host_controls_passed"] = True
        pulled = run([docker, "pull", IMAGE], timeout=180, category="image_pull")
        if pulled.returncode:
            raise ProbeError("image_pull_failed")
        inspected = run([docker, "image", "inspect", IMAGE, "--format", "{{json .RepoDigests}}"],
                        timeout=30, category="image_inspect")
        if inspected.returncode:
            raise ProbeError("image_inspect_failed")
        digests = parse_json(inspected.stdout, "image_inspect")
        if not isinstance(digests, list):
            raise ProbeError("image_digest_missing")
        matches = [value for value in digests if isinstance(value, str) and DIGEST.fullmatch(value)]
        if len(matches) != 1:
            raise ProbeError("image_digest_missing")
        digest = matches[0]
        report["image_digest"] = digest
        name = "c2s-public-repository-" + role + "-" + uuid.uuid4().hex
        command = [
            docker, "run", "--rm", "--name", name, "--pull", "never",
            "--network", "none", "--user", f"{uid}:{gid}", "--read-only",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--pids-limit", "32", "--memory", "128m", "--memory-swap", "128m",
            "--cpus", "1", "--ipc", "none", "--workdir", "/repo",
            "--mount", f"type=bind,source={root / role},target=/repo",
            "--entrypoint", "/usr/bin/env", digest, "-i",
            "PATH=/usr/local/bin:/usr/bin:/bin", "/usr/local/bin/python3", "-I", "-B",
            "-c", PROBE, role, commit, str(uid), str(gid), str(root),
        ]
        try:
            worker = run(command, timeout=90, category="worker")
        finally:
            # Only this invocation's unique name is eligible for forced removal.
            try:
                run([docker, "rm", "--force", name], timeout=30, category="cleanup")
            except ProbeError:
                pass
        after = snapshot(root)
        output_key = role + "/" + OUTPUT
        output_state = after.pop(output_key, None)
        host_unchanged = after == before
        report["host_repositories_unchanged"] = host_unchanged
        expected_output = "PUBLIC SYNTHETIC PROBE OUTPUT\nrole=" + role + "\n"
        host_output = (output_state is not None and
                       (root / role / OUTPUT).read_text(encoding="utf-8") == expected_output)
        report["host_output_control_passed"] = host_output
        value = parse_json(worker.stdout, "worker")
        if (not isinstance(value, dict) or set(value) != {"status", "checks"} or
                value.get("status") not in ("passed", "failed") or
                not isinstance(value.get("checks"), dict) or
                set(value["checks"]) != set(CHECKS) or
                any(type(item) is not bool for item in value["checks"].values())):
            raise ProbeError("worker_invalid_schema")
        report["worker_checks"] = value["checks"]
        if (worker.returncode != 0 or value["status"] != "passed" or
                not all(value["checks"].values()) or not host_unchanged or not host_output):
            raise ProbeError("worker_boundary_checks_failed")
        report["container_repo_boundary_passed"] = True
        report["status"] = "synthetic_probe_passed"


def main() -> int:
    report = {
        "format": 1, "synthetic_only": True, "role": None, "source_commit": None,
        "image_digest": None, "job_workspace_scope": "separate-ci-job",
        "host_controls_passed": False, "host_repositories_unchanged": False,
        "host_output_control_passed": False, "worker_checks": {name: False for name in CHECKS},
        "container_repo_boundary_passed": False, "native_subagent_scoping_verified": False,
        "full_role_delivery_ready": False, "development_ready": False, "status": "failed",
    }
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=ROLES)
    try:
        arguments = parser.parse_args()
        report["role"] = arguments.role
        probe(arguments.role, report)
    except ProbeError as error:
        report["error"] = str(error)
    except (OSError, ValueError, UnicodeError, TypeError, KeyError):
        report["error"] = "filesystem_or_input_error"
    except Exception:
        report["error"] = "unexpected_probe_failure"
    if "error" in report:
        # Even a late TemporaryDirectory cleanup failure must keep the gate shut.
        report["container_repo_boundary_passed"] = False
        report["status"] = "failed"
    print(json.dumps(report, sort_keys=True))
    return 0 if report["container_repo_boundary_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
