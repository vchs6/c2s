#!/usr/bin/env python3
"""Read-only Linux public-tool checks; never an implementation readiness gate."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
COMMAND_TIMEOUT_SECONDS = 10


def check_command(argv, pattern, *, env=None):
    """Return only a classification and a numeric version, never raw output."""
    try:
        result = subprocess.run(
            argv,
            cwd=ROOT,
            env=env,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return {"status": "missing", "version": None}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "version": None}
    except OSError:
        return {"status": "error", "version": None}
    if result.returncode != 0:
        return {"status": "error", "version": None}
    match = re.fullmatch(pattern, result.stdout.strip())
    if match is None:
        return {"status": "error", "version": None}
    return {"status": "ok", "version": match.group(1).decode("ascii")}


def main():
    python_version = sys.version_info[:3]
    checks = {
        "python": {
            "status": "ok" if python_version >= (3, 11, 0) else "unsupported_version",
            "version": ".".join(map(str, python_version)),
        }
    }
    if sys.platform != "linux":
        # No .cmd/shell fallback or unverified platform-specific package path.
        checks.update({
            name: {"status": "error", "version": None, "reason": "unsupported_platform"}
            for name in ("node", "npm", "git", "openspec")
        })
    else:
        checks["node"] = check_command(["node", "--version"], rb"v([0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6})")
        if checks["node"]["status"] == "ok":
            version = tuple(map(int, checks["node"]["version"].split(".")))
            if not ((22, 13, 0) <= version < (23, 0, 0) or version >= (24, 0, 0)):
                checks["node"]["status"] = "unsupported_version"
        checks["npm"] = check_command(["npm", "--version"], rb"([0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6})")
        checks["git"] = check_command(
            ["git", "--version"], rb"git version ([0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}(?:\.[0-9]{1,6})?)"
        )
        openspec_env = os.environ.copy()
        openspec_env["OPENSPEC_TELEMETRY"] = "0"
        checks["openspec"] = check_command(
            [str(ROOT / "node_modules" / ".bin" / "openspec"), "--version"],
            rb"([0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6})",
            env=openspec_env,
        )
    ready = all(check["status"] == "ok" for check in checks.values())
    print(json.dumps({
        "format": 1,
        "scope": "public-preparation-only",
        "checks": checks,
        "available_runtimes": {name: shutil.which(name) is not None for name in ("docker", "podman")},
        "public_tools_ready": ready,
        "readiness_complete": False,
        "isolation_ready": False,
        "implementation_started": False,
        "limitations": [
            "Only Linux host execution is supported; other platforms return error.",
            "Native subagent availability, model access and model identity are not verified.",
            "Five-role permission isolation, private acceptance and controlled handoff are not verified.",
            "Runtime command presence does not verify runtime execution or isolation.",
            "Public tool checks never authorize product implementation or pass product gates.",
        ],
    }, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
