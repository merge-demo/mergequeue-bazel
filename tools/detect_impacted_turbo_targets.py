#!/usr/bin/env python3
"""
Detect impacted Turbo targets based on git changes.

This script uses git diff to determine which packages are impacted by changes
between a base and head commit (or uncommitted changes), then formats them as
Turbo targets (package-name#task).
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set


def find_turbo_workspace_root(repo_root: Path) -> Optional[Path]:
    """
    Find the Turbo workspace root directory (should contain turbo.json and package.json).
    Returns the path to the turbo directory, or None if not found.
    """
    # Check if turbo directory exists
    turbo_dir = repo_root / "turbo"
    if (turbo_dir / "turbo.json").exists() and (turbo_dir / "package.json").exists():
        return turbo_dir
    return None


def get_all_packages(turbo_dir: Path) -> List[str]:
    """
    Get all packages in the Turbo workspace by reading package.json files.

    Returns:
        List of package names (e.g., ['@mergequeue/alpha', '@mergequeue/bravo'])
    """
    packages = []

    # Check packages directory
    packages_dir = turbo_dir / "packages"
    if packages_dir.exists():
        for pkg_dir in packages_dir.iterdir():
            if pkg_dir.is_dir():
                pkg_json = pkg_dir / "package.json"
                if pkg_json.exists():
                    try:
                        with open(pkg_json, "r", encoding="utf-8") as f:
                            pkg_data = json.load(f)
                            pkg_name = pkg_data.get("name")
                            if pkg_name:
                                packages.append(pkg_name)
                    except (json.JSONDecodeError, IOError):
                        pass

    # Check apps directory
    apps_dir = turbo_dir / "apps"
    if apps_dir.exists():
        for app_dir in apps_dir.iterdir():
            if app_dir.is_dir():
                app_json = app_dir / "package.json"
                if app_json.exists():
                    try:
                        with open(app_json, "r", encoding="utf-8") as f:
                            app_data = json.load(f)
                            app_name = app_data.get("name")
                            if app_name:
                                packages.append(app_name)
                    except (json.JSONDecodeError, IOError):
                        pass

    return sorted(packages)


def get_changed_files(
    base: Optional[str] = None,
    head: Optional[str] = None,
    uncommitted: bool = False,
    untracked: bool = False,
) -> List[str]:
    """
    Get list of changed files using git diff.

    Args:
        base: Base commit/branch
        head: Head commit
        uncommitted: Include uncommitted changes
        untracked: Include untracked files

    Returns:
        List of changed file paths
    """
    changed_files = []

    try:
        if base and head:
            # Compare two commits
            result = subprocess.run(
                ["git", "diff", "--name-only", base, head],
                capture_output=True,
                text=True,
                check=True,
            )
            changed_files.extend(result.stdout.strip().split("\n"))
        elif uncommitted:
            # Get uncommitted changes
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            changed_files.extend(result.stdout.strip().split("\n"))

        if untracked:
            # Get untracked files
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True,
                text=True,
                check=True,
            )
            changed_files.extend(result.stdout.strip().split("\n"))

        # Filter out empty strings
        return [f for f in changed_files if f.strip()]

    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        if e.stderr:
            print(f"Error output: {e.stderr}", file=sys.stderr)
        return []


def map_files_to_packages(changed_files: List[str], turbo_dir: Path) -> Set[str]:
    """
    Map changed files to affected packages.

    Args:
        changed_files: List of changed file paths
        turbo_dir: Path to turbo workspace root

    Returns:
        Set of affected package names
    """
    affected_packages = set()

    # Normalize turbo_dir path for comparison
    turbo_dir_str = str(turbo_dir.resolve())

    for file_path in changed_files:
        if not file_path.strip():
            continue

        # Check if file is in turbo workspace
        full_path = Path(file_path).resolve()
        if turbo_dir_str not in str(full_path):
            continue

        # Try to find which package this file belongs to
        # Check packages directory
        packages_dir = turbo_dir / "packages"
        if packages_dir.exists():
            for pkg_dir in packages_dir.iterdir():
                if pkg_dir.is_dir():
                    pkg_path_str = str(pkg_dir.resolve())
                    if pkg_path_str in str(full_path):
                        pkg_json = pkg_dir / "package.json"
                        if pkg_json.exists():
                            try:
                                with open(pkg_json, "r", encoding="utf-8") as f:
                                    pkg_data = json.load(f)
                                    pkg_name = pkg_data.get("name")
                                    if pkg_name:
                                        affected_packages.add(pkg_name)
                            except (json.JSONDecodeError, IOError):
                                pass

        # Check apps directory
        apps_dir = turbo_dir / "apps"
        if apps_dir.exists():
            for app_dir in apps_dir.iterdir():
                if app_dir.is_dir():
                    app_path_str = str(app_dir.resolve())
                    if app_path_str in str(full_path):
                        app_json = app_dir / "package.json"
                        if app_json.exists():
                            try:
                                with open(app_json, "r", encoding="utf-8") as f:
                                    app_data = json.load(f)
                                    app_name = app_data.get("name")
                                    if app_name:
                                        affected_packages.add(app_name)
                            except (json.JSONDecodeError, IOError):
                                pass

        # Also check if turbo.json or root package.json changed (affects all packages)
        if "turbo/turbo.json" in file_path or "turbo/package.json" in file_path:
            # If root config changed, all packages are affected
            all_packages = get_all_packages(turbo_dir)
            affected_packages.update(all_packages)

    return affected_packages


def format_turbo_targets(packages: Set[str], task: str = "build") -> List[str]:
    """
    Format package names as Turbo targets (package-name#task).

    Args:
        packages: Set of package names
        task: Task name (default: "build")

    Returns:
        List of formatted targets
    """
    targets = []
    for pkg in sorted(packages):
        # Format as package-name#task
        targets.append(f"{pkg}#{task}")
    return targets


def write_impacted_targets_json(
    targets: List[str],
    output_file: str = "impacted_targets_json_tmp",
    verbose: bool = True,
):
    """
    Write the list of impacted Turbo targets to a JSON file.
    """
    # Convert to sorted list for consistent output
    target_list = sorted(list(set(targets)))  # Remove duplicates and sort

    try:
        # Write as JSON array
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(target_list, f)

        if verbose:
            print(f"Wrote {len(target_list)} impacted Turbo targets to {output_file}")
            if target_list:
                print("Impacted Turbo targets:")
                for target in target_list:
                    print(f"  - {target}")
            else:
                print("No impacted Turbo targets found")

    except IOError as e:
        print(f"Error writing to {output_file}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main function to detect impacted Turbo targets and write to JSON file.
    """
    parser = argparse.ArgumentParser(
        description="Detect impacted Turbo targets from git changes"
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
        help="Base commit/branch for comparison (e.g., 'main', 'HEAD~1'). "
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
        "--uncommitted",
        action="store_true",
        help="Include uncommitted changes",
    )
    parser.add_argument(
        "--untracked",
        action="store_true",
        help="Include untracked files",
    )
    parser.add_argument(
        "--turbo-dir",
        type=str,
        help="Path to Turbo workspace directory (default: auto-detect 'turbo' directory)",
    )
    parser.add_argument(
        "--task",
        type=str,
        default="build",
        help="Task name to append to targets (default: build)",
    )

    args = parser.parse_args()

    # Determine repository root (current directory or parent)
    repo_root = Path.cwd().resolve()
    if not (repo_root / ".git").exists():
        # Try parent directory
        parent = repo_root.parent
        if (parent / ".git").exists():
            repo_root = parent
        else:
            print("Error: Not in a git repository", file=sys.stderr)
            sys.exit(1)

    # Find Turbo workspace
    if args.turbo_dir:
        turbo_dir = Path(args.turbo_dir).resolve()
    else:
        turbo_dir = find_turbo_workspace_root(repo_root)

    if not turbo_dir or not turbo_dir.exists():
        print(
            "Error: Turbo workspace not found. Expected 'turbo' directory with turbo.json and package.json",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.quiet:
        print(f"Using Turbo workspace at: {turbo_dir}")

    # Get changed files
    changed_files = []
    if args.files:
        changed_files = [f.strip() for f in args.files.split(",")]
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

    # Map files to packages
    affected_packages = map_files_to_packages(changed_files, turbo_dir)

    # Format as Turbo targets
    targets = format_turbo_targets(affected_packages, task=args.task)

    # Write to JSON file
    write_impacted_targets_json(targets, args.output, not args.quiet)


if __name__ == "__main__":
    main()
