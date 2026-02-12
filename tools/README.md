# Tools

This folder contains scripts for detecting impacted targets and uploading them to Trunk.

## Scripts

### `detect_impacted_nx_targets.py`

Detects impacted Nx projects/targets based on git changes using Nx's affected command.

**Usage:**

```bash
# Check affected projects between a base commit and HEAD
python3 tools/detect_impacted_nx_targets.py --base=main

# Check affected projects for uncommitted changes
python3 tools/detect_impacted_nx_targets.py --uncommitted

# Check affected projects for specific files
python3 tools/detect_impacted_nx_targets.py --files="nx/alpha/alpha.txt,nx/bravo/bravo.txt"

# Custom output file
python3 tools/detect_impacted_nx_targets.py --base=HEAD~1 -o nx_targets.json
```

**Options:**

- `--base BASE`: Base commit/branch for comparison (e.g., 'main', 'HEAD~1')
- `--head HEAD`: Head commit (default: HEAD)
- `--files FILES`: Comma-separated list of specific files to check
- `--uncommitted`: Include uncommitted changes
- `--untracked`: Include untracked files
- `-o, --output OUTPUT`: Output file path (default: impacted_targets_json_tmp)
- `-q, --quiet`: Suppress verbose output

**Output:** Writes a JSON array of affected project names to the output file.

### `detect_impacted_uv_targets.py`

Detects impacted UV workspace packages based on git changes. Uses `uv.lock` to build the dependency
graph and propagates impact to dependents (e.g. changing `uv-common` impacts all libs and the app).

**Usage:**

```bash
# Check affected packages between a base commit and HEAD
python3 tools/detect_impacted_uv_targets.py --base=main

# Check affected packages for uncommitted changes
python3 tools/detect_impacted_uv_targets.py --uncommitted

# Check affected packages for specific files
python3 tools/detect_impacted_uv_targets.py --files="uv/lib/alpha/alpha.py,uv/lib/common/common.py"

# Custom output file
python3 tools/detect_impacted_uv_targets.py --base=HEAD~1 -o uv_targets.json
```

**Options:**

- `--base BASE`: Base commit/branch for comparison (e.g., 'main', 'HEAD~1')
- `--head HEAD`: Head commit (default: HEAD)
- `--files FILES`: Comma-separated list of specific files to check
- `--uncommitted`: Include uncommitted changes
- `--untracked`: Include untracked files
- `-o, --output OUTPUT`: Output file path (default: impacted_targets_json_tmp)
- `-q, --quiet`: Suppress verbose output
- `--workspace PATH`: Repo root (default: auto-detect from cwd)

**Output:** Writes a JSON array of affected UV package names to the output file. Use with
`upload_targets.py` to report impacted targets to Trunk (e.g. when `build == 'uv'` in the mergequeue
config).

### `upload_targets.py`

Generic script to upload a JSON array of impacted targets to the Trunk API. Used by the Nx, Turbo,
and UV PR target actions.

### `upload_glob_targets.py`

Uploads impacted targets to Trunk API.

### `glob_targets.sh`

Helper script for glob-based target detection.
