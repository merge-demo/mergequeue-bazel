#!/usr/bin/env python3
"""
Upload impacted targets to Trunk API.

This script reads impacted targets from a JSON file and uploads them to Trunk's API.
It's a generic script that works for any build system (Nx, Turbo, Bazel, etc.).
"""

import json
import os
import sys
from typing import Optional

import requests
import typer

app = typer.Typer(help="Upload impacted targets to Trunk API")


def eprint(*args, **kwargs):
    """Print to stderr."""
    print(*args, file=sys.stderr, **kwargs)


@app.command()
def main(
    targets_file: str = typer.Option(
        ...,
        "--targets-file",
        help="Path to JSON file containing impacted targets (array of strings)",
    ),
    trunk_token: Optional[str] = typer.Option(
        None,
        "--trunk-token",
        envvar="TRUNK_TOKEN",
        help="Trunk API token (or set TRUNK_TOKEN env var)",
    ),
    api_url: str = typer.Option(
        "https://api.trunk.io:443/v1/setImpactedTargets",
        "--api-url",
        help="Trunk API URL",
    ),
    repository: Optional[str] = typer.Option(
        None,
        "--repository",
        envvar="GITHUB_REPOSITORY",
        help="Repository in format 'owner/name' (or set GITHUB_REPOSITORY env var)",
    ),
    pr_number: Optional[str] = typer.Option(
        None,
        "--pr-number",
        help="Pull request number (or set PR_NUMBER/GITHUB_EVENT_NUMBER env var)",
    ),
    pr_sha: Optional[str] = typer.Option(
        None,
        "--pr-sha",
        help="Pull request head SHA (or set PR_SHA/GITHUB_SHA env var)",
    ),
    target_branch: Optional[str] = typer.Option(
        None,
        "--target-branch",
        help="Target branch name (or set TARGET_BRANCH/GITHUB_BASE_REF env var)",
    ),
):
    """Upload impacted targets to Trunk API."""
    # Get token from arg or env
    if not trunk_token:
        eprint("Error: Trunk token required (--trunk-token or TRUNK_TOKEN env var)")
        sys.exit(1)

    # Read impacted targets
    try:
        with open(targets_file, "r", encoding="utf-8") as f:
            impacted_targets = json.load(f)
        if not isinstance(impacted_targets, list):
            eprint(f"Error: Expected JSON array in {targets_file}")
            sys.exit(1)
    except FileNotFoundError:
        eprint(f"Error: Targets file not found: {targets_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        eprint(f"Error: Invalid JSON in targets file: {e}")
        sys.exit(1)

    # Get repository and PR information from args or environment variables
    # (typer handles GITHUB_REPOSITORY, but we need to check multiple env vars for others)
    if not pr_number:
        pr_number = os.environ.get("PR_NUMBER") or os.environ.get("GITHUB_EVENT_NUMBER")
    if not pr_sha:
        pr_sha = os.environ.get("PR_SHA") or os.environ.get("GITHUB_SHA")
    if not target_branch:
        target_branch = os.environ.get("TARGET_BRANCH") or os.environ.get(
            "GITHUB_BASE_REF"
        )

    # Parse repository owner and name
    if repository:
        try:
            repo_owner, repo_name = repository.split("/", 1)
        except ValueError:
            eprint(
                f"Error: Repository must be in format 'owner/name', got: {repository}"
            )
            sys.exit(1)
    else:
        eprint("Error: Repository required (--repository or GITHUB_REPOSITORY env var)")
        sys.exit(1)

    # Validate required fields
    if not pr_number:
        eprint(
            "Error: PR number required (--pr-number, PR_NUMBER, or GITHUB_EVENT_NUMBER env var)"
        )
        sys.exit(1)
    if not pr_sha:
        eprint("Error: PR SHA required (--pr-sha, PR_SHA, or GITHUB_SHA env var)")
        sys.exit(1)
    if not target_branch:
        eprint(
            "Error: Target branch required (--target-branch, TARGET_BRANCH, or GITHUB_BASE_REF env var)"
        )
        sys.exit(1)

    # Convert PR number to int
    try:
        pr_number_int = int(pr_number)
    except (ValueError, TypeError):
        eprint(f"Error: PR number must be an integer, got: {pr_number}")
        sys.exit(1)

    # Build API request body
    post_body = {
        "repo": {"host": "github.com", "owner": repo_owner, "name": repo_name},
        "pr": {"number": pr_number_int, "sha": pr_sha},
        "targetBranch": target_branch,
        "impactedTargets": impacted_targets,
    }

    # Make API request
    headers = {"Content-Type": "application/json", "x-api-token": trunk_token}
    try:
        response = requests.post(api_url, headers=headers, json=post_body, timeout=30)
        http_status_code = response.status_code
    except requests.RequestException as e:
        eprint(f"HTTP request failed: {e}")
        sys.exit(1)

    # Handle response
    if http_status_code == 200:
        num_targets = len(impacted_targets)
        print(
            f"✨ Uploaded {num_targets} impacted targets for PR #{pr_number_int} @ {pr_sha}"
        )
        sys.exit(0)
    else:
        eprint(f"❌ Failed to upload impacted targets. HTTP {http_status_code}")
        try:
            error_body = response.json()
            eprint(f"Response: {json.dumps(error_body, indent=2)}")
        except (ValueError, json.JSONDecodeError):
            eprint(f"Response: {response.text}")
        sys.exit(1)


if __name__ == "__main__":
    app()
