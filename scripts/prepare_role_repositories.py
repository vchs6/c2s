#!/usr/bin/env python3
"""Prepare public role snapshots; this is not a role permission broker.

Only explicitly allowed committed blobs enter fresh repositories. No endpoint or
tool permissions are restricted by this utility. A failed publication may leave
the destination that this invocation exclusively created; it never deletes an
existing destination or retries by overwriting it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ROLES = ("coding", "review", "author", "runner", "verifier")
CONTRACTS = (
    "openspec/specs/independent-delivery/spec.md",
    "openspec/specs/semantic-fact-query/spec.md",
)
CANDIDATE = "scripts/check_public_environment.py"
GENERATED_FILES = ("ROLE_INPUT.json", "PUBLIC_SYNTHETIC_MARKER.txt")
MAX_BLOB_BYTES = 16 * 1024 * 1024
TIMEOUT_SECONDS = 20
SHA1 = re.compile(r"[0-9a-f]{40}\Z")


class PreparationError(Exception):
    """Only fixed, public error categories may escape the implementation."""


def safe_error(category: str) -> dict:
    return {
        "error": category,
        "repository_setup_passed": False,
        "permission_isolation_verified": False,
        "development_ready": False,
    }


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's message may include arbitrary user-supplied input.
        raise PreparationError("invalid_arguments")


def git_environment() -> dict[str, str]:
    # Do not inherit GIT_*, authentication helpers, signing or model settings.
    environment = {
        "PATH": os.defpath,
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_AUTHOR_NAME": "c2s Public Snapshot",
        "GIT_AUTHOR_EMAIL": "public-snapshot@example.invalid",
        "GIT_COMMITTER_NAME": "c2s Public Snapshot",
        "GIT_COMMITTER_EMAIL": "public-snapshot@example.invalid",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
    }
    # Required by native Git on Windows; no arbitrary environment is inherited.
    if "SYSTEMROOT" in os.environ:
        environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return environment


def run_git(executable: str, repository: Path, *arguments: str) -> bytes:
    command = [
        executable,
        "-c", "core.hooksPath=" + os.devnull,
        "-c", "core.fsmonitor=false",
        "-c", "core.attributesFile=" + os.devnull,
        "-c", "core.autocrlf=false",
        "-c", "commit.gpgSign=false",
        "-c", "tag.gpgSign=false",
        "-c", "gc.auto=0",
        "-c", "maintenance.auto=false",
        "-c", "protocol.allow=never",
        "-C", str(repository),
        *arguments,
    ]
    try:
        result = subprocess.run(
            command,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=git_environment(),
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise PreparationError("git_timeout") from None
    except OSError:
        raise PreparationError("git_unavailable") from None
    if result.returncode != 0:
        raise PreparationError("git_operation_failed")
    return result.stdout


def fixed_commit(executable: str, source: Path, reference: str) -> str:
    if not reference or "\x00" in reference or len(reference) > 4096:
        raise PreparationError("invalid_reference")
    value = run_git(
        executable, source, "rev-parse", "--verify", "--end-of-options",
        reference + "^{commit}",
    ).strip()
    try:
        commit = value.decode("ascii")
    except UnicodeDecodeError:
        raise PreparationError("invalid_source_commit") from None
    if SHA1.fullmatch(commit) is None:
        raise PreparationError("invalid_source_commit")
    return commit


def public_blobs(executable: str, source: Path, commit: str) -> dict:
    blobs = {}
    for path in (*CONTRACTS, CANDIDATE):
        entry = run_git(executable, source, "ls-tree", "-z", commit, "--", path)
        records = entry.split(b"\0")
        if len(records) != 2 or records[-1] != b"":
            raise PreparationError("source_path_not_regular_blob")
        try:
            metadata, stored_path = records[0].split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
        except (ValueError, UnicodeDecodeError):
            raise PreparationError("source_path_not_regular_blob") from None
        if (stored_path != path.encode("utf-8")
                or mode not in ("100644", "100755")
                or object_type != "blob"
                or SHA1.fullmatch(object_id) is None):
            raise PreparationError("source_path_not_regular_blob")
        size_text = run_git(executable, source, "cat-file", "-s", object_id).strip()
        if not size_text.isdigit() or int(size_text) > MAX_BLOB_BYTES:
            raise PreparationError("source_blob_too_large")
        content = run_git(executable, source, "cat-file", "blob", object_id)
        if len(content) != int(size_text):
            raise PreparationError("source_blob_size_mismatch")
        blobs[path] = {
            "content": content,
            "mode": mode,
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    return blobs


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_role(executable: str, root: Path, template: Path, role: str,
              source_commit: str, blobs: dict) -> dict:
    repository = root / role
    repository.mkdir()
    paths = CONTRACTS if role == "author" else (*CONTRACTS, CANDIDATE)
    files = [{"path": path, "sha256": blobs[path]["sha256"]} for path in paths]
    for path in paths:
        target = repository / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blobs[path]["content"])
        target.chmod(0o755 if blobs[path]["mode"] == "100755" else 0o644)
    write_json(repository / "ROLE_INPUT.json", {
        "role": role,
        "source_commit": source_commit,
        "files": files,
        "synthetic_only": True,
    })
    (repository / "PUBLIC_SYNTHETIC_MARKER.txt").write_text(
        "PUBLIC SYNTHETIC MARKER\n"
        f"role={role}\n"
        "Public synthetic data only; no hidden assertions or private suite.\n"
        "Role names do not enforce identity or tool permissions.\n",
        encoding="utf-8",
    )
    run_git(executable, repository, "init", "--quiet", "--initial-branch=main",
            "--object-format=sha1", "--template=" + str(template))
    run_git(executable, repository, "add", "--", *paths, *GENERATED_FILES)
    run_git(executable, repository, "commit", "--quiet", "--no-verify",
            "--no-gpg-sign", "-m", f"Public synthetic snapshot for {role}")
    role_commit = run_git(executable, repository, "rev-parse", "--verify", "HEAD").strip().decode("ascii")
    if SHA1.fullmatch(role_commit) is None:
        raise PreparationError("invalid_role_commit")
    return {"path": role, "role_commit": role_commit, "files": files}


def prepare(source_argument: str, reference: str, destination_argument: str) -> dict:
    executable = shutil.which("git", path=os.defpath)
    if executable is None:
        raise PreparationError("git_unavailable")
    source = Path(source_argument).resolve(strict=True)
    if not source.is_dir():
        raise PreparationError("invalid_source")
    raw_destination = Path(os.path.abspath(destination_argument))
    # Resolve the parent only: resolving the leaf would hide dangling symlinks.
    parent = raw_destination.parent.resolve(strict=True)
    destination = parent / raw_destination.name
    if os.path.lexists(destination):
        raise PreparationError("destination_exists")
    if not parent.is_dir():
        raise PreparationError("invalid_destination_parent")
    commit = fixed_commit(executable, source, reference)
    blobs = public_blobs(executable, source, commit)
    temporary = Path(tempfile.mkdtemp(prefix=".c2s-role-preparation-", dir=parent))
    try:
        template = temporary / "empty-template"
        template.mkdir()
        payload = temporary / "payload"
        payload.mkdir()
        roles = {
            role: make_role(executable, payload, template, role, commit, blobs)
            for role in ROLES
        }
        manifest = {
            "format": 1,
            "scope": "public-role-repositories-only",
            "source_commit": commit,
            "roles": roles,
            "repository_setup_passed": True,
            "permission_isolation_verified": False,
            "development_ready": False,
        }
        write_json(payload / "MANIFEST.json", manifest)
        # mkdir is an exclusive reservation, including against dangling symlinks.
        # A rename of the whole tree could replace a concurrent empty directory.
        try:
            destination.mkdir()
        except FileExistsError:
            raise PreparationError("destination_exists") from None
        for entry in payload.iterdir():
            entry.rename(destination / entry.name)
        return manifest
    finally:
        # Only this invocation's private staging directory is eligible for cleanup.
        shutil.rmtree(temporary)


def main() -> int:
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--ref", required=True, dest="reference")
    parser.add_argument("--destination", required=True)
    try:
        arguments = parser.parse_args()
        manifest = prepare(arguments.source, arguments.reference, arguments.destination)
    except PreparationError as error:
        print(json.dumps(safe_error(str(error)), sort_keys=True))
        return 1
    except (OSError, ValueError, UnicodeError):
        print(json.dumps(safe_error("filesystem_or_input_error"), sort_keys=True))
        return 1
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
