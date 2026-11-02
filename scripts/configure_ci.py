#!/usr/bin/env python3
"""Plan or apply GitHub CI account configuration without exposing credentials."""

import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import warnings


class ConfigurationError(Exception):
    """A safe error category; never include raw CLI output."""


def repository(value):
    parts = value.split("/")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("expected owner/repository")
    owner, name = parts
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", owner):
        raise argparse.ArgumentTypeError("invalid repository owner")
    if "--" in owner or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", name) or name in {".", ".."}:
        raise argparse.ArgumentTypeError("invalid repository name")
    return value


def gh(arguments, *, data=None, allow_missing=False):
    try:
        result = subprocess.run(
            ["gh", *arguments], input=data, text=True, capture_output=True,
            check=False, timeout=120, errors="replace",
            env={**os.environ, "GH_HOST": "github.com"},
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ConfigurationError("github_cli_unavailable_or_timed_out") from None
    if result.returncode:
        if allow_missing and "HTTP 404" in result.stderr:
            return None
        raise ConfigurationError("github_cli_request_failed")
    return result.stdout


def api_object(endpoint, *, allow_missing=False):
    raw = gh(["api", endpoint], allow_missing=allow_missing)
    if raw is None:
        return None
    try:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise ConfigurationError("invalid_github_api_response") from None


def inspect_repository(name, *, allow_missing=False):
    info = api_object(f"repos/{name}", allow_missing=allow_missing)
    if info is None:
        return None
    try:
        if info["full_name"].lower() != name.lower() or not isinstance(info["private"], bool):
            raise ValueError
        return info
    except (ValueError, KeyError, TypeError):
        raise ConfigurationError("invalid_repository_response") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repository", type=repository, default="vchs6/c2s")
    parser.add_argument("--acceptance-repository", type=repository, default="vchs6/c2s-acceptance")
    parser.add_argument("--apply", action="store_true", help="apply using an already authenticated local gh")
    parser.add_argument("--set-model-key", action="store_true", help="on apply, securely prompt once and set OPENAI_API_KEY on both repositories")
    args = parser.parse_args()
    if args.source_repository.lower() == args.acceptance_repository.lower():
        parser.error("source and acceptance repositories must differ")
    report = {
        "mode": "apply" if args.apply else "dry-run",
        "source_repository": args.source_repository,
        "acceptance_repository": args.acceptance_repository,
        "development_ready": False,
        "scope": "account_bootstrap_only",
        "role_boundary_verified": False,
        "bootstrap_configured": False,
        "source_workflow_state": "not_checked",
        "model_key_set": False,
        "completed_steps": [],
        "plan": [
            "verify authenticated gh and source repository",
            "verify or create private acceptance repository; reject public repository",
            "set and read back source ACCEPTANCE_REPOSITORY and acceptance SOURCE_REPOSITORY variables",
            "enable repository Actions if disabled, preserving allowed_actions policy; read back",
            "set and read back both Actions defaults: read, pull request approval disabled",
            "securely prompt and set OPENAI_API_KEY on both repositories" if args.set_model_key else "leave model credentials unchanged",
            "check source isolation-readiness workflow is active; missing or disabled remains blocked",
        ],
    }
    if not args.apply:
        report["status"] = "planned"
        print(json.dumps(report, ensure_ascii=False))
        return 0
    try:
        if shutil.which("gh") is None:
            raise ConfigurationError("gh_not_installed")
        try:
            gh(["auth", "status", "--hostname", "github.com"])
        except ConfigurationError:
            raise ConfigurationError("authentication_required") from None
        inspect_repository(args.source_repository)
        report["completed_steps"].append("source_verified")
        info = inspect_repository(args.acceptance_repository, allow_missing=True)
        if info is None:
            gh(["repo", "create", args.acceptance_repository, "--private"])
            report["completed_steps"].append("acceptance_repository_created")
            info = inspect_repository(args.acceptance_repository)
        if not info["private"]:
            raise ConfigurationError("acceptance_repository_is_public")
        report["completed_steps"].append("acceptance_private_verified")
        for repo, variable, value in [
            (args.source_repository, "ACCEPTANCE_REPOSITORY", args.acceptance_repository),
            (args.acceptance_repository, "SOURCE_REPOSITORY", args.source_repository),
        ]:
            gh(["variable", "set", variable, "--repo", repo, "--body", value])
            variable_info = api_object(f"repos/{repo}/actions/variables/{variable}")
            if variable_info.get("value") != value:
                raise ConfigurationError("repository_variable_readback_mismatch")
            report["completed_steps"].append(f"{variable}_verified")
        for repo in (args.source_repository, args.acceptance_repository):
            endpoint = f"repos/{repo}/actions/permissions"
            actions = api_object(endpoint)
            if not isinstance(actions.get("enabled"), bool):
                raise ConfigurationError("invalid_actions_permissions_response")
            if not actions["enabled"]:
                gh(["api", "--method", "PUT", endpoint, "-F", "enabled=true"])
            actual_actions = api_object(endpoint)
            if actual_actions.get("enabled") is not True:
                raise ConfigurationError("repository_actions_not_enabled")
            if actual_actions.get("allowed_actions") != actions.get("allowed_actions"):
                raise ConfigurationError("actions_policy_changed_during_configuration")
            report["completed_steps"].append(f"actions_enabled_verified:{repo}")
            gh(["api", "--method", "PUT", f"repos/{repo}/actions/permissions/workflow",
                "-f", "default_workflow_permissions=read", "-F", "can_approve_pull_request_reviews=false"])
            defaults = api_object(f"repos/{repo}/actions/permissions/workflow")
            if (defaults.get("default_workflow_permissions") != "read"
                    or defaults.get("can_approve_pull_request_reviews") is not False):
                raise ConfigurationError("actions_defaults_readback_mismatch")
            report["completed_steps"].append(f"actions_defaults_verified:{repo}")
        if args.set_model_key:
            if not sys.stdin.isatty():
                raise ConfigurationError("interactive_terminal_required_for_model_key")
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    key = getpass.getpass("OPENAI_API_KEY (hidden): ")
            except (getpass.GetPassWarning, EOFError):
                raise ConfigurationError("secure_model_key_input_unavailable") from None
            if not key.strip() or any(c in key for c in "\r\n\0"):
                raise ConfigurationError("invalid_model_key_input")
            try:
                for repo in (args.source_repository, args.acceptance_repository):
                    gh(["secret", "set", "OPENAI_API_KEY", "--repo", repo], data=key)
                    report["completed_steps"].append(f"model_key_set:{repo}")
                report["model_key_set"] = True
            finally:
                key = None
        report["bootstrap_configured"] = True
        workflow = api_object(
            f"repos/{args.source_repository}/actions/workflows/isolation-readiness.yml",
            allow_missing=True,
        )
        state = workflow.get("state") if workflow else None
        report["source_workflow_state"] = "active" if state == "active" else "missing_or_inaccessible" if workflow is None else "inactive"
        if state != "active":
            raise ConfigurationError("source_isolation_workflow_not_active")
        report["completed_steps"].append("source_workflow_active_verified")
        report["status"] = "account_bootstrap_applied"
        exit_code = 0
    except ConfigurationError as error:
        report["status"] = "blocked"
        report["error"] = str(error)
        exit_code = 1
    except KeyboardInterrupt:
        report["status"] = "blocked"
        report["error"] = "interrupted"
        exit_code = 130
    print(json.dumps(report, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
