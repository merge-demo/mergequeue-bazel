#!/usr/bin/env python3
"""
Detect impacted UV workspace packages based on git changes.

This script uses git diff to determine which workspace packages are impacted
by changes between a base and head commit (or uncommitted changes), then
propagates impact to dependents using the dependency graph from uv.lock.
"""

import argparse
import json
import subprocess  # noqa: B404  # bandit: git is a trusted control-plane tool
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set


def _parse_uv_lock(lock_path: Path) -> tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    Parse uv.lock for workspace members without external TOML deps.
    Returns (path_by_name, dependents) for workspace packages only.
    """
    # pylint: disable=too-many-branches,too-many-locals,too-many-statements
    text = lock_path.read_text(encoding="utf-8")
    members: Set[str] = set()
    in_manifest_members = False
    for line in text.splitlines():
        if line.strip() == "[manifest]":
            in_manifest_members = False
        if "members = [" in line or (
            in_manifest_members and line.strip().startswith('"')
        ):
            in_manifest_members = True
            for part in line.split('"'):
                if len(part) == 0:
                    continue
                name = part.strip(" ,\n")
                if name and not name.startswith("]"):
                    members.add(name)
        if "]" in line and in_manifest_members:
            in_manifest_members = False
    if not members:
        return {}, {}

    path_by_name: Dict[str, str] = {}
    deps_by_name: Dict[str, List[str]] = {}
    current_name: Optional[str] = None
    current_editable: Optional[str] = None
    current_deps: List[str] = []
    in_deps = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[[package]]"):
            if current_name and current_name in members:
                path_by_name[current_name] = current_editable or ""
                deps_by_name[current_name] = [d for d in current_deps if d in members]
            current_name = None
            current_editable = None
            current_deps = []
            in_deps = False
            continue
        if stripped.startswith('name = "'):
            current_name = stripped.split('"')[1]
        # Only take editable from "source = { editable = \"...\" }", not requires-dist
        if stripped.startswith("source = ") and 'editable = "' in line:
            for i, part in enumerate(line.split('"')):
                if i % 2 == 1 and i >= 1:
                    current_editable = part.rstrip("/")
                    break
        if stripped.startswith("dependencies = ["):
            in_deps = True
            for part in line.split('"'):
                if len(part) == 0:
                    continue
                name = part.strip(" ,\n")
                if name and name in members:
                    current_deps.append(name)
        elif in_deps:
            if "]" in line:
                for part in line.split('"'):
                    name = part.strip(" ,\n")
                    if name and name in members:
                        current_deps.append(name)
                in_deps = False
            else:
                for part in line.split('"'):
                    name = part.strip(" ,\n")
                    if name and name in members:
                        current_deps.append(name)

    if current_name and current_name in members:
        path_by_name[current_name] = current_editable or ""
        deps_by_name[current_name] = [d for d in current_deps if d in members]

    dependents: Dict[str, List[str]] = {n: [] for n in path_by_name}
    for pkg, deps in deps_by_name.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].append(pkg)
    return path_by_name, dependents


def find_repo_root(start: Path) -> Optional[Path]:
    """Find git repository root. Returns None if not in a repo."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return current if (current / ".git").exists() else None


def find_uv_workspace(repo_root: Path) -> Optional[Path]:
    """
    Find UV workspace root (directory containing pyproject.toml with
    [tool.uv.workspace] and uv.lock).
    """
    root_pyproject = repo_root / "pyproject.toml"
    root_lock = repo_root / "uv.lock"
    if root_pyproject.exists() and root_lock.exists():
        try:
            content = root_pyproject.read_text(encoding="utf-8")
            if "[tool.uv.workspace]" in content or "uv.workspace" in content:
                return repo_root
        except IOError:
            pass
    return None


def load_workspace_packages(
    repo_root: Path,
) -> tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    Parse uv.lock for workspace members: package name -> editable path (relative to repo),
    and dependency graph: package name -> list of direct workspace dependency names.

    Returns:
        (path_by_name, dependents)
        path_by_name: e.g. {"uv-alpha": "uv/lib/alpha", ...}
        dependents: reverse graph, e.g. {"uv-common": ["uv-alpha", "uv-bravo", ...]}
    """
    lock_path = repo_root / "uv.lock"
    if not lock_path.exists():
        return {}, {}
    return _parse_uv_lock(lock_path)


def get_changed_files(
    base: Optional[str] = None,
    head: Optional[str] = None,
    uncommitted: bool = False,
    untracked: bool = False,
) -> List[str]:
    """Get list of changed file paths via git diff."""
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


def map_files_to_directly_changed_packages(
    changed_files: List[str],
    path_by_name: Dict[str, str],
    repo_root: Path,
) -> Set[str]:
    """
    Map changed file paths to directly changed workspace package names.
    Root pyproject.toml or uv.lock triggers all packages.
    """
    directly_changed: Set[str] = set()
    root_str = str(repo_root.resolve())

    for f in changed_files:
        if not f.strip():
            continue
        path = Path(f).resolve()
        try:
            path_str = str(path)
        except OSError:
            continue
        if root_str not in path_str:
            continue
        try:
            rel = path.relative_to(repo_root)
        except ValueError:
            continue
        rel_str = str(rel).replace("\\", "/")

        if rel_str in ("pyproject.toml", "uv.lock"):
            directly_changed.update(path_by_name.keys())
            continue
        if rel_str.startswith("uv/"):
            for name, pkg_dir in path_by_name.items():
                if not pkg_dir:
                    continue
                if rel_str == pkg_dir or rel_str.startswith(pkg_dir + "/"):
                    directly_changed.add(name)
                    break

    return directly_changed


def propagate_to_dependents(
    directly_changed: Set[str],
    dependents: Dict[str, List[str]],
) -> Set[str]:
    """Return directly changed packages plus all dependents (BFS)."""
    impacted = set(directly_changed)
    queue = list(directly_changed)
    while queue:
        pkg = queue.pop()
        for dep in dependents.get(pkg, []):
            if dep not in impacted:
                impacted.add(dep)
                queue.append(dep)
    return impacted


def write_impacted_targets_json(
    targets: List[str],
    output_file: str,
    verbose: bool = True,
) -> None:
    """Write JSON array of impacted package names to file."""
    target_list = sorted(set(targets))
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(target_list, f)
    if verbose:
        print(f"Wrote {len(target_list)} impacted UV targets to {output_file}")
        if target_list:
            print("Impacted UV targets:")
            for t in target_list:
                print(f"  - {t}")
        else:
            print("No impacted UV targets found")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect impacted UV workspace packages from git changes",
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
        help="Comma-separated list of specific files to check",
    )
    parser.add_argument(
        "--uncommitted", action="store_true", help="Include uncommitted changes"
    )
    parser.add_argument(
        "--untracked", action="store_true", help="Include untracked files"
    )
    parser.add_argument(
        "--workspace",
        type=str,
        help="Path to repo root (default: auto-detect from cwd)",
    )
    args = parser.parse_args()

    cwd = Path.cwd().resolve()
    repo_root = find_repo_root(cwd)
    if not repo_root:
        print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)
    if args.workspace:
        repo_root = Path(args.workspace).resolve()

    workspace_root = find_uv_workspace(repo_root)
    if not workspace_root or not (workspace_root / "uv.lock").exists():
        print(
            "Error: UV workspace not found. Expected repo root with pyproject.toml "
            "[tool.uv.workspace] and uv.lock",
            file=sys.stderr,
        )
        sys.exit(1)

    path_by_name, dependents = load_workspace_packages(workspace_root)
    if not path_by_name:
        print("Error: No workspace members found in uv.lock", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"Using UV workspace at: {workspace_root}")

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
            print(f"Checking affected packages between {args.base} and {args.head}")
        elif args.files:
            print(f"Checking affected packages for files: {', '.join(changed_files)}")
        else:
            print("Checking affected packages for uncommitted changes")
        if changed_files:
            print(f"Found {len(changed_files)} changed files")

    directly_changed = map_files_to_directly_changed_packages(
        changed_files, path_by_name, workspace_root
    )
    impacted = propagate_to_dependents(directly_changed, dependents)
    write_impacted_targets_json(list(impacted), args.output, verbose=not args.quiet)


if __name__ == "__main__":
    main()
