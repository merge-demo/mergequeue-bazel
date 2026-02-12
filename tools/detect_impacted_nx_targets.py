#!/usr/bin/env python3
"""
Detect impacted Nx targets based on git changes.

This script uses Nx's affected command to determine which projects are
impacted by changes between a base and head commit (or uncommitted changes).
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def find_nx_workspace_root(repo_root: Path) -> Optional[Path]:
    """
    Find the Nx workspace root directory (should contain nx.json and package.json).
    Returns the path to the nx directory, or None if not found.
    """
    # Check if nx directory exists
    nx_dir = repo_root / "nx"
    if (nx_dir / "nx.json").exists() and (nx_dir / "package.json").exists():
        return nx_dir
    return None


def run_nx_command(
    nx_dir: Path,
    base: Optional[str] = None,
    head: Optional[str] = None,
    files: Optional[List[str]] = None,
    uncommitted: bool = False,
    untracked: bool = False,
) -> List[str]:
    """
    Run Nx affected command to get list of impacted projects.

    Args:
        nx_dir: Path to the Nx workspace directory
        base: Base commit/branch (e.g., 'main', 'HEAD~1')
        head: Head commit (default: 'HEAD')
        files: List of specific files to check
        uncommitted: Include uncommitted changes
        untracked: Include untracked files

    Returns:
        List of affected project names
    """
    cmd = ["npx", "nx", "show", "projects", "--affected", "--json"]

    # Add base/head arguments
    if base:
        cmd.extend(["--base", base])
    if head:
        cmd.extend(["--head", head])

    # Add file-based detection
    if files:
        cmd.extend(["--files", ",".join(files)])

    # Add uncommitted/untracked flags
    if uncommitted:
        cmd.append("--uncommitted")
    if untracked:
        cmd.append("--untracked")

    try:
        result = subprocess.run(
            cmd,
            cwd=nx_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse JSON output
        if result.stdout.strip():
            projects = json.loads(result.stdout.strip())
            return projects if isinstance(projects, list) else []
        return []

    except subprocess.CalledProcessError as e:
        print(f"Error running Nx command: {e}", file=sys.stderr)
        if e.stderr:
            print(f"Error output: {e.stderr}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing Nx output as JSON: {e}", file=sys.stderr)
        print(f"Output was: {result.stdout}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print(
            "Error: npx command not found. Make sure Node.js and npm are installed.",
            file=sys.stderr,
        )
        return []


def write_impacted_targets_json(
    projects: List[str],
    output_file: str = "impacted_targets_json_tmp",
    verbose: bool = True,
):
    """
    Write the list of impacted Nx projects to a JSON file.
    """
    # Convert to sorted list for consistent output
    project_list = sorted(list(set(projects)))  # Remove duplicates and sort

    try:
        # Write as JSON array
        with open(output_file, "w") as f:
            json.dump(project_list, f)

        if verbose:
            print(f"Wrote {len(project_list)} impacted Nx projects to {output_file}")
            if project_list:
                print("Impacted Nx projects:")
                for project in project_list:
                    print(f"  - {project}")
            else:
                print("No impacted Nx projects found")

    except IOError as e:
        print(f"Error writing to {output_file}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main function to detect impacted Nx targets and write to JSON file.
    """
    parser = argparse.ArgumentParser(
        description="Detect impacted Nx targets from git changes using Nx affected command"
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
        "--nx-dir",
        type=str,
        help="Path to Nx workspace directory (default: auto-detect 'nx' directory)",
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

    # Find Nx workspace
    if args.nx_dir:
        nx_dir = Path(args.nx_dir).resolve()
    else:
        nx_dir = find_nx_workspace_root(repo_root)

    if not nx_dir or not nx_dir.exists():
        print(
            f"Error: Nx workspace not found. Expected 'nx' directory with nx.json and package.json",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.quiet:
        print(f"Using Nx workspace at: {nx_dir}")

    # Parse files argument
    files = None
    if args.files:
        files = [f.strip() for f in args.files.split(",")]

    # Determine which mode to use
    # Nx requires either base/head OR uncommitted/untracked (mutually exclusive)
    use_uncommitted = args.uncommitted or (not args.base and not args.files)
    use_untracked = (
        args.untracked and not use_uncommitted
    )  # Only if uncommitted not set

    # Run Nx affected command
    if not args.quiet:
        if args.base:
            print(f"Checking affected projects between {args.base} and {args.head}")
        elif args.files:
            print(f"Checking affected projects for files: {', '.join(files)}")
        elif use_uncommitted:
            print("Checking affected projects for uncommitted changes")
        elif use_untracked:
            print("Checking affected projects for untracked changes")
        else:
            print("Checking affected projects for uncommitted changes")

    affected_projects = run_nx_command(
        nx_dir=nx_dir,
        base=args.base if args.base else None,
        head=args.head if args.base else None,
        files=files,
        uncommitted=use_uncommitted,
        untracked=use_untracked,
    )

    # Write to JSON file
    write_impacted_targets_json(affected_projects, args.output, not args.quiet)


if __name__ == "__main__":
    main()
