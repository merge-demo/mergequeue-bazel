# UV Workspace Usage Guide

This workspace contains individual packages for each word list (alpha, bravo, charlie, etc.).

## Setup

First, sync all workspace packages:

```bash
uv sync --all-packages
```

## Running

### 1. Run the wordcounter application

After syncing the workspace, you can run the wordcounter application:

```bash
uv run python -m wordcounter
```
