#!/usr/bin/env python3
import json
import os
import sys

import requests


# Helper to print to stderr
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def main():
    # 1. Check required environment variables
    required_env = [
        "API_TOKEN",
        "REPOSITORY",
        "TARGET_BRANCH",
        "PR_NUMBER",
        "PR_SHA",
        "IMPACTED_TARGETS_FILE",
    ]
    for var in required_env:
        if not os.environ.get(var):
            eprint(f"Missing required environment variable: {var}")
            sys.exit(2)

    API_TOKEN = os.environ["API_TOKEN"]
    REPOSITORY = os.environ["REPOSITORY"]
    TARGET_BRANCH = os.environ["TARGET_BRANCH"]
    PR_NUMBER = os.environ["PR_NUMBER"]
    PR_SHA = os.environ["PR_SHA"]
    IMPACTED_TARGETS_FILE = os.environ["IMPACTED_TARGETS_FILE"]
    IMPACTS_ALL_DETECTED = os.environ.get("IMPACTS_ALL_DETECTED", "false")
    API_URL = os.environ.get(
        "API_URL", "https://api.trunk.io:443/v1/setImpactedTargets"
    )
    ACTOR = os.environ.get("ACTOR", "")

    # 2. Parse repo owner and name
    try:
        REPO_OWNER, REPO_NAME = REPOSITORY.split("/", 1)
    except ValueError:
        eprint("REPOSITORY must be in the form 'owner/name'")
        sys.exit(2)

    # 3. Build JSON bodies
    repo_body = {"host": "github.com", "owner": REPO_OWNER, "name": REPO_NAME}
    pr_body = {"number": PR_NUMBER, "sha": PR_SHA}

    # 4. Build POST body
    if IMPACTS_ALL_DETECTED == "true":
        post_body = {
            "repo": repo_body,
            "pr": pr_body,
            "targetBranch": TARGET_BRANCH,
            "impactedTargets": "ALL",
        }
        num_impacted_targets = "'ALL'"
    else:
        # Read impacted targets from file, convert to JSON array
        try:
            with open(IMPACTED_TARGETS_FILE, "r") as f:
                impacted_targets = [line.strip() for line in f if line.strip()]
        except Exception as e:
            eprint(f"Error reading impacted targets file: {e}")
            sys.exit(2)
        post_body = {
            "repo": repo_body,
            "pr": pr_body,
            "targetBranch": TARGET_BRANCH,
            "impactedTargets": impacted_targets,
        }
        num_impacted_targets = str(len(impacted_targets))

    # 5. POST to API
    headers = {"Content-Type": "application/json", "x-api-token": API_TOKEN}
    try:
        response = requests.post(API_URL, headers=headers, json=post_body)
        http_status_code = response.status_code
    except Exception as e:
        eprint(f"HTTP request failed: {e}")
        sys.exit(1)

    # 6. Handle response
    exit_code = 0
    if http_status_code == 200:
        comment_text = f"✨ Uploaded {num_impacted_targets} impacted targets for {PR_NUMBER} @ {PR_SHA}"
    else:
        exit_code = 1
        comment_text = f"❌ Unable to upload impacted targets. Encountered {http_status_code} @ {PR_SHA}. Please contact us at slack.trunk.io."
        if http_status_code == 401:
            if ACTOR == "dependabot[bot]":
                comment_text = (
                    "❌ Unable to upload impacted targets. Did you update your Dependabot secrets with your repo's token? "
                    "See https://docs.github.com/en/code-security/dependabot/working-with-dependabot/automating-dependabot-with-github-actions#accessing-secrets for more details."
                )
            elif ACTOR.endswith("[bot]"):
                comment_text = "❌ Unable to upload impacted targets. Please verify that this bot has access to your repo's token."

    print(comment_text)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
