#!/usr/bin/env python3
"""
Detect impacted Buck2 targets based on git changes.

This script uses git diff to determine which files changed between a base and
head commit (or uncommitted changes), maps them to their owning Buck2 targets
with `buck2 uquery owner(...)`, then propagates impact to every target that
depends on them with `buck2 uquery rdeps(...)`.
"""

import argparse
import json
import os
import shutil
import subprocess  # noqa: B404  # bandit: git and buck2 are trusted control-plane tools
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Set

UNIVERSE = "root//..."

# Files (relative to the Buck2 project root) that affect every target.
GLOBAL_FILES = {".buckconfig", ".buckroot", "bin/buck2"}
GLOBAL_DIRS = ("toolchains/",)

BUILD_FILE_NAMES = {"BUCK", "BUCK.v2", "TARGETS", "TARGETS.v2"}

# DotSlash file (relative to the Buck2 project root) that pins the buck2 version.
PINNED_BUCK2 = "bin/buck2"


def find_repo_root(start: Path) -> Optional[Path]:
    """Find git repository root. Returns None if not in a repo."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return current if (current / ".git").exists() else None


def find_buck2_root(repo_root: Path) -> Optional[Path]:
    """
    Find the Buck2 project root (directory containing .buckconfig).
    Returns the path to the buck2 directory, or None if not found.
    """
    buck2_dir = repo_root / "buck2"
    if (buck2_dir / ".buckconfig").exists():
        return buck2_dir
    return None


def get_changed_files(
    base: Optional[str] = None,
    head: Optional[str] = None,
    uncommitted: bool = False,
    untracked: bool = False,
) -> List[str]:
    """Get list of changed file paths (relative to the repo root) via git diff."""
    changed = []
    try:
        if base and head:
            result = (
                subprocess.run(  # noqa: B603,B607  # nosec B603,B607 - git from PATH
                    ["git", "diff", "--name-only", base, head],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            )
            changed.extend(result.stdout.strip().split("\n"))
        elif uncommitted:
            result = (
                subprocess.run(  # noqa: B603,B607  # nosec B603,B607 - git from PATH
                    ["git", "diff", "--name-only", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            )
            changed.extend(result.stdout.strip().split("\n"))

        if untracked:
            result = (
                subprocess.run(  # noqa: B603,B607  # nosec B603,B607 - git from PATH
                    ["git", "ls-files", "--others", "--exclude-standard"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            )
            changed.extend(result.stdout.strip().split("\n"))

        return [f.strip() for f in changed if f.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return []


def run_uquery(buck2: str, buck2_root: Path, query: str) -> List[str]:
    """Run `buck2 uquery` and return the resulting target labels."""
    # Pass the query through an argfile so long file lists don't hit argv limits.
    with tempfile.NamedTemporaryFile(
        "w", suffix=".args", delete=False, encoding="utf-8"
    ) as argfile:
        argfile.write(query + "\n")
    try:
        result = subprocess.run(  # noqa: B603  # nosec B603 - buck2 from PATH
            [buck2, "uquery", "--output-format", "json", f"@{argfile.name}"],
            cwd=buck2_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running buck2 uquery: {query}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)
    finally:
        os.unlink(argfile.name)
    return json.loads(result.stdout or "[]")


def nearest_package(rel_path: str, buck2_root: Path) -> Optional[str]:
    """Return the closest ancestor directory of rel_path that has a build file."""
    parts = Path(rel_path).parts[:-1]
    for i in range(len(parts), -1, -1):
        pkg_dir = buck2_root.joinpath(*parts[:i])
        if any((pkg_dir / name).exists() for name in BUILD_FILE_NAMES):
            return "/".join(parts[:i])
    return None


def build_seed_query(changed_files: List[str], buck2_root: Path) -> Optional[str]:
    """
    Turn changed files (relative to the Buck2 root) into a query expression
    for the directly changed targets. Returns None if nothing is impacted.

    - .buckconfig, .buckroot, bin/buck2 (the pinned version, which also pins the
      bundled prelude), toolchains/ and .bzl changes impact everything.
    - A changed build file impacts every target in its package.
    - A changed source file impacts the targets that own it. If the file was
      deleted, every target in its nearest surviving package is impacted.
    """
    terms: List[str] = []
    for rel in sorted(set(changed_files)):
        name = Path(rel).name
        if rel in GLOBAL_FILES or rel.startswith(GLOBAL_DIRS) or rel.endswith(".bzl"):
            return UNIVERSE
        if name in BUILD_FILE_NAMES:
            if (buck2_root / rel).exists():
                pkg = str(Path(rel).parent).replace("\\", "/")
                terms.append(f"root//{'' if pkg == '.' else pkg}:")
            continue
        if (buck2_root / rel).exists():
            terms.append(f"owner('{rel}')")
        else:
            surviving = nearest_package(rel, buck2_root)
            if surviving is not None:
                terms.append(f"root//{surviving}:")
    if not terms:
        return None
    return " + ".join(terms)


def detect_impacted_targets(
    changed_files: List[str],
    repo_root: Path,
    buck2_root: Path,
    buck2: str,
) -> Set[str]:
    """Map changed repo files to impacted Buck2 targets, including reverse deps."""
    prefix = str(buck2_root.relative_to(repo_root)).replace("\\", "/") + "/"
    in_project = [f[len(prefix) :] for f in changed_files if f.startswith(prefix)]
    seed = build_seed_query(in_project, buck2_root)
    if seed is None:
        return set()
    if seed == UNIVERSE:
        return set(run_uquery(buck2, buck2_root, UNIVERSE))
    return set(run_uquery(buck2, buck2_root, f"rdeps({UNIVERSE}, {seed})"))


def resolve_buck2(override: Optional[str], buck2_root: Path) -> str:
    """Return the buck2 executable: the override, or the pinned DotSlash file."""
    if override:
        return override
    pinned = str(buck2_root / PINNED_BUCK2)
    if not shutil.which("dotslash"):
        print(
            f"Error: {pinned} is a DotSlash file but dotslash is not on PATH. "
            "Install it from https://dotslash-cli.com or pass --buck2=buck2",
            file=sys.stderr,
        )
        sys.exit(1)
    return pinned


def write_impacted_targets_json(
    targets: List[str],
    output_file: str,
    verbose: bool = True,
) -> None:
    """Write JSON array of impacted target labels to file."""
    target_list = sorted(set(targets))
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(target_list, f)
    if verbose:
        print(f"Wrote {len(target_list)} impacted Buck2 targets to {output_file}")
        if target_list:
            print("Impacted Buck2 targets:")
            for t in target_list:
                print(f"  - {t}")
        else:
            print("No impacted Buck2 targets found")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect impacted Buck2 targets from git changes",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="impacted_targets_json_tmp",
        help="Output file path (default: impacted_targets_json_tmp)",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress verbose output"
    )
    parser.add_argument(
        "--base",
        type=str,
        help="Base commit/branch for comparison (e.g. main, HEAD~1). "
        "If not specified, uses uncommitted changes.",
    )
    parser.add_argument(
        "--head",
        type=str,
        default="HEAD",
        help="Head commit for comparison (default: HEAD)",
    )
    parser.add_argument(
        "--files",
        type=str,
        help="Comma-separated list of specific files to check (relative to repo root)",
    )
    parser.add_argument(
        "--uncommitted", action="store_true", help="Include uncommitted changes"
    )
    parser.add_argument(
        "--untracked", action="store_true", help="Include untracked files"
    )
    parser.add_argument(
        "--buck2-dir",
        type=str,
        help="Path to Buck2 project root (default: auto-detect 'buck2' directory)",
    )
    parser.add_argument(
        "--buck2",
        type=str,
        help=f"buck2 executable to invoke (default: the pinned DotSlash file "
        f"<buck2-dir>/{PINNED_BUCK2}, which requires dotslash on PATH)",
    )
    args = parser.parse_args()

    repo_root = find_repo_root(Path.cwd())
    if not repo_root:
        print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)

    buck2_root: Optional[Path]
    if args.buck2_dir:
        buck2_root = Path(args.buck2_dir).resolve()
    else:
        buck2_root = find_buck2_root(repo_root)

    if not buck2_root or not (buck2_root / ".buckconfig").exists():
        print(
            "Error: Buck2 project not found. Expected 'buck2' directory with .buckconfig",
            file=sys.stderr,
        )
        sys.exit(1)

    buck2 = resolve_buck2(args.buck2, buck2_root)

    if not args.quiet:
        print(f"Using Buck2 project at: {buck2_root}")

    if args.files:
        changed_files = [f.strip() for f in args.files.split(",") if f.strip()]
    else:
        changed_files = get_changed_files(
            base=args.base if args.base else None,
            head=args.head if args.base else None,
            uncommitted=args.uncommitted or (not args.base and not args.files),
            untracked=args.untracked,
        )

    if not args.quiet:
        if args.base:
            print(f"Checking affected targets between {args.base} and {args.head}")
        elif args.files:
            print(f"Checking affected targets for files: {', '.join(changed_files)}")
        else:
            print("Checking affected targets for uncommitted changes")
        if changed_files:
            print(f"Found {len(changed_files)} changed files")

    impacted = detect_impacted_targets(changed_files, repo_root, buck2_root, buck2)
    write_impacted_targets_json(list(impacted), args.output, verbose=not args.quiet)


if __name__ == "__main__":
    main()
