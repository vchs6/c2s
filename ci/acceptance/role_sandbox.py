#!/usr/bin/env python3
"""Trusted-host role launcher and public, synthetic-only boundary diagnostic.

run_role is for a trusted coordinator, never a model-selectable host tool. The
coordinator owns root, image selection, argv and all handoffs. It must not expose
this API, the Docker CLI/socket, host shell, or this root to an untrusted role.
This diagnostic deploys neither model sessions nor a product acceptance suite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import uuid


ROLE_UIDS = {
    "coding": 10001, "review": 10002, "author": 10003,
    "runner": 10004, "verifier": 10005, "candidate": 10006,
}
MOUNTS = {
    "coding": {"public": "ro", "candidate": "rw"},
    "review": {"public": "ro", "candidate": "ro", "review": "rw"},
    "author": {"public": "ro", "suite": "rw"},
    "runner": {"public": "ro", "candidate": "ro", "suite": "ro", "run": "rw"},
    "verifier": {"public": "ro", "candidate": "ro", "review": "ro",
                 "suite": "ro", "run": "ro", "verdict": "rw"},
    "candidate": {"public": "ro", "candidate": "ro"},
}
AREAS = ("public", "candidate", "review", "suite", "run", "verdict", "host-only")
IMAGE = "python:3.12-slim"
DIGEST = re.compile(r"(?:[a-z0-9.-]+(?::[0-9]+)?/)?[a-z0-9/_-]+@sha256:[0-9a-f]{64}\Z")
HOST_ENV = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/nonexistent", "DOCKER_CONFIG": "/nonexistent",
}


def _docker(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    # No shell, inherited credential/config variables, or raw failure output.
    return subprocess.run(["docker", *args], capture_output=True, text=True,
                          timeout=timeout, check=False, env=HOST_ENV)


def run_role(root: Path, role: str, argv: list[str], image: str) -> subprocess.CompletedProcess:
    """Execute one trusted-coordinator command inside a fresh restricted role.

    root must be a coordinator-owned absolute canonical directory containing
    the seven real area directories. image must be an already-resolved public
    RepoDigest. No role may choose these host-side arguments or change mounts.
    The returned process output is untrusted and must not be logged verbatim.
    """
    if role not in ROLE_UIDS or not argv or not all(isinstance(x, str) and x for x in argv):
        raise ValueError("invalid_role_command")
    if not isinstance(image, str) or not DIGEST.fullmatch(image):
        raise ValueError("immutable_image_required")
    root = Path(root)
    if not root.is_absolute() or root != root.resolve(strict=True) or not root.is_dir():
        raise ValueError("canonical_coordinator_root_required")
    for area in AREAS:
        path = root / area
        if path.is_symlink() or not path.is_dir() or path.resolve(strict=True).parent != root:
            raise ValueError("real_area_directory_required")
        if "," in str(path):
            raise ValueError("invalid_mount_path")
    uid = ROLE_UIDS[role]
    container_name = "public-role-" + role + "-" + uuid.uuid4().hex
    args = [
        "run", "--rm", "--name", container_name, "--pull", "never", "--network", "none",
        "--user", f"{uid}:{uid}", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true", "--pids-limit", "32",
        "--memory", "128m", "--memory-swap", "128m", "--cpus", "1",
        # The default PID namespace is private; never set host/container joins.
        "--ipc", "none", "--workdir", "/",
        "--entrypoint", "/usr/bin/env",
    ]
    for area, mode in MOUNTS[role].items():
        args += ["--mount", f"type=bind,source={root / area},target=/{area}"
                 + (",readonly" if mode == "ro" else "")]
    # Clear image ENV too. No -e/--env-file, host volumes, sockets or PID joins.
    args += [image, "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent",
             "LC_ALL=C.UTF-8", *argv]
    try:
        return _docker(args, timeout=120)
    except subprocess.TimeoutExpired:
        _docker(["rm", "--force", container_name], timeout=30)
        raise RuntimeError("role_timeout") from None


# Public control values only. This code is placed in the read-only /public mount.
PROBE = r'''
import json, os, pathlib, re, socket, sys

role, uid, host_root, host_pid, host_uid, matrix_json = sys.argv[1:]
matrix = json.loads(matrix_json)
areas = ("public", "candidate", "review", "suite", "run", "verdict", "host-only")
checks = {}

def denied_read(path):
    try:
        pathlib.Path(path).read_bytes()
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        return True
    return False

def denied_write(path):
    try:
        with pathlib.Path(path).open("ab") as stream:
            stream.write(b"PUBLIC-SYNTHETIC-FORBIDDEN-WRITE\n")
    except (FileNotFoundError, PermissionError, OSError):
        return True
    return False

checks["uid_gid"] = os.getuid() == int(uid) and os.getgid() == int(uid)
checks["empty_sensitive_environment"] = dict(os.environ) == {
    "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent", "LC_ALL": "C.UTF-8"}
checks["legal_reads"] = all(
    pathlib.Path("/" + area + "/marker.txt").read_text() ==
    "PUBLIC-SYNTHETIC-" + area + "\n" for area in matrix)
checks["unmounted_reads_denied"] = all(
    denied_read("/" + area + "/marker.txt") for area in areas if area not in matrix)
checks["forbidden_writes_denied"] = all(
    denied_write("/" + area + "/marker.txt") for area in areas if matrix.get(area) != "rw")
owned = [area for area, mode in matrix.items() if mode == "rw"]
checks["exclusive_output_write"] = not owned
if owned:
    output = pathlib.Path("/" + owned[0] + "/role-output.txt")
    output.write_text("PUBLIC-SYNTHETIC-OUTPUT-" + role + "\n")
    checks["exclusive_output_write"] = output.read_text() == "PUBLIC-SYNTHETIC-OUTPUT-" + role + "\n"
checks["host_paths_denied"] = all(denied_read(path) for path in (
    host_root + "/host-only/marker.txt", host_root + "/public/marker.txt",
    "/proc/1/root" + host_root + "/host-only/marker.txt"))
checks["host_process_credentials_denied"] = (
    os.getpid() == 1 and denied_read("/proc/" + host_pid + "/environ") and
    b"PUBLIC_SYNTHETIC_CREDENTIAL" not in pathlib.Path("/proc/1/environ").read_bytes())
sockets = ("/var/run/docker.sock", "/run/docker.sock", "/run/containerd/containerd.sock",
           "/run/user/" + host_uid + "/docker.sock")
checks["management_sockets_denied"] = all(not pathlib.Path(path).exists() for path in sockets)
checks["rootfs_read_only"] = all(denied_write(path) for path in (
    "/rootfs-write-probe", "/tmp/rootfs-write-probe", "/etc/passwd"))
checks["network_none"] = {p.name for p in pathlib.Path("/sys/class/net").iterdir()} == {"lo"}
status = pathlib.Path("/proc/self/status").read_text().splitlines()
status = dict(line.split(":", 1) for line in status if ":" in line)
checks["privileges_restricted"] = (
    status.get("NoNewPrivs", "").strip() == "1" and
    int(status.get("CapEff", "1").strip(), 16) == 0)
# GitHub-hosted Ubuntu uses cgroup v2; an unknown layout fails closed.
cgroup = pathlib.Path("/sys/fs/cgroup")
cpu = (cgroup / "cpu.max").read_text().split()
checks["resource_limits"] = (
    (cgroup / "pids.max").read_text().strip() == "32" and
    (cgroup / "memory.max").read_text().strip() == "134217728" and
    cpu[0].isdigit() and cpu[1].isdigit() and int(cpu[0]) == int(cpu[1]))
hostname = socket.gethostname()
checks["container_identity"] = bool(re.fullmatch("[0-9a-f]{12}", hostname))
print(json.dumps({"checks": checks, "container": hostname}, sort_keys=True))
sys.exit(0 if all(checks.values()) else 1)
'''

CHECKS = (
    "uid_gid", "empty_sensitive_environment", "legal_reads", "unmounted_reads_denied",
    "forbidden_writes_denied", "exclusive_output_write", "host_paths_denied",
    "host_process_credentials_denied", "management_sockets_denied", "rootfs_read_only",
    "network_none", "privileges_restricted", "resource_limits", "container_identity",
)


def _snapshot(root: Path, excluded: str | None) -> dict:
    """Detect modification/creation/deletion/symlinks in every forbidden area."""
    result = {}
    for area in AREAS:
        if area == excluded:
            continue
        paths = [root / area, *(root / area).rglob("*")]
        for path in paths:
            mode = path.lstat().st_mode
            if stat.S_ISREG(mode):
                value = hashlib.sha256(path.read_bytes()).hexdigest()
            elif stat.S_ISDIR(mode):
                value = "directory"
            elif stat.S_ISLNK(mode):
                value = "symlink:" + os.readlink(path)
            else:
                value = "special"
            result[str(path.relative_to(root))] = [stat.S_IMODE(mode), value]
    return result


def probe() -> dict:
    report = {
        "synthetic_only": True, "development_ready": False,
        "status": "failed", "image_digest": None, "roles": {},
        "independent_containers": False, "host_control_read": False,
        "host_forbidden_areas_unchanged": False,
    }
    sentinel = None
    try:
        pulled = _docker(["pull", IMAGE])
        if pulled.returncode:
            raise RuntimeError("image_pull_failed")
        inspected = _docker(["image", "inspect", IMAGE, "--format", "{{json .RepoDigests}}"])
        if inspected.returncode:
            raise RuntimeError("image_inspect_failed")
        digests = json.loads(inspected.stdout)
        digest = next(d for d in digests if isinstance(d, str)
                      and d.startswith("python@sha256:") and DIGEST.fullmatch(d))
        report["image_digest"] = digest
        with tempfile.TemporaryDirectory(prefix="public-role-boundary-") as directory:
            root = Path(directory).resolve()
            for area in AREAS:
                path = root / area
                path.mkdir(mode=0o755)
                # Namespace mounts provide exclusivity; host runner need not chown.
                path.chmod(0o755 if area in ("public", "host-only") else 0o777)
                marker = path / "marker.txt"
                marker.write_text("PUBLIC-SYNTHETIC-" + area + "\n")
                marker.chmod(0o666)
            (root / "public" / "probe.py").write_text(PROBE)
            (root / "public" / "probe.py").chmod(0o644)
            sentinel = subprocess.Popen(
                [sys.executable, "-I", "-c", "import sys; sys.stdin.buffer.read()"],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={"PUBLIC_SYNTHETIC_CREDENTIAL": "PUBLIC-NOT-A-SECRET"})
            report["host_control_read"] = (
                (root / "host-only" / "marker.txt").read_text() == "PUBLIC-SYNTHETIC-host-only\n"
                and b"PUBLIC_SYNTHETIC_CREDENTIAL=PUBLIC-NOT-A-SECRET" in
                Path(f"/proc/{sentinel.pid}/environ").read_bytes())
            containers = set()
            unchanged = True
            for role, uid in ROLE_UIDS.items():
                owned = next((area for area, mode in MOUNTS[role].items() if mode == "rw"), None)
                before = _snapshot(root, owned)
                process = run_role(root, role, [
                    "python", "-I", "-B", "/public/probe.py", role, str(uid), str(root),
                    str(sentinel.pid), str(os.getuid()), json.dumps(MOUNTS[role], sort_keys=True),
                ], digest)
                intact = before == _snapshot(root, owned)
                unchanged = unchanged and intact
                role_result = {name: False for name in CHECKS}
                role_result["host_forbidden_areas_unchanged"] = intact
                role_result["passed"] = False
                # Never print arbitrary container stdout/stderr or exception text.
                if len(process.stdout) <= 8192:
                    try:
                        value = json.loads(process.stdout)
                        checks = value["checks"]
                        for name in CHECKS:
                            role_result[name] = checks.get(name) is True
                        identity = value["container"]
                        if isinstance(identity, str) and re.fullmatch(r"[0-9a-f]{12}", identity):
                            containers.add(identity)
                        if owned:
                            expected = "PUBLIC-SYNTHETIC-OUTPUT-" + role + "\n"
                            role_result["exclusive_output_write"] = (
                                role_result["exclusive_output_write"] and
                                (root / owned / "role-output.txt").read_text() == expected)
                        role_result["passed"] = process.returncode == 0 and all(role_result[k] for k in CHECKS) and intact
                    except (ValueError, KeyError, TypeError, AttributeError, OSError):
                        pass
                report["roles"][role] = role_result
            report["host_forbidden_areas_unchanged"] = unchanged
            report["independent_containers"] = len(containers) == len(ROLE_UIDS)
            if (report["host_control_read"] and unchanged and report["independent_containers"]
                    and all(item["passed"] for item in report["roles"].values())):
                report["status"] = "synthetic_probe_passed"
    except Exception:
        report["error"] = "synthetic_boundary_diagnostic_failed"
    finally:
        if sentinel is not None:
            if sentinel.stdin:
                sentinel.stdin.close()
            try:
                sentinel.wait(timeout=5)
            except subprocess.TimeoutExpired:
                sentinel.kill()
                sentinel.wait(timeout=5)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="run only public synthetic checks")
    args = parser.parse_args()
    if not args.probe:
        parser.error("--probe is required; run_role is a trusted Python API only")
    result = probe()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "synthetic_probe_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
