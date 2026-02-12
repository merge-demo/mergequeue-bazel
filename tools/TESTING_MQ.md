# Testing the `mq` Tool Locally

The `mq` tool is downloaded from the `trunk-io/mergequeue-tool` repository releases. Here's how to
test it locally:

## 1. Download the `mq` Tool

### Option A: Download from GitHub Releases

```bash
# Get the latest release
curl -L -o mq.tar.gz https://github.com/trunk-io/mergequeue-tool/releases/latest/download/mq-$(uname -m)-unknown-linux-gnu.tar.gz

# Extract it
tar -xzf mq.tar.gz

# Make it executable
chmod +x mq

# Test it works
./mq --help
```

### Option B: Use the release-downloader action approach (manual)

```bash
# Download using gh CLI (if you have it)
gh release download -R trunk-io/mergequeue-tool --pattern "*.tar.gz" --dir /tmp

# Or manually download from:
# https://github.com/trunk-io/mergequeue-tool/releases
```

## 2. Set Up Environment Variables

You'll need:

- `TRUNK_TOKEN`: Your Trunk API token (from app.trunk.io)
- `GH_TOKEN` or `GITHUB_TOKEN`: Your GitHub personal access token (for PR operations)

```bash
export TRUNK_TOKEN="your-trunk-token-here"
export GH_TOKEN="your-github-token-here"
# Or
export GITHUB_TOKEN="your-github-token-here"
```

## 3. Test Commands

### Check Configuration

```bash
./mq config
```

This will read `.config/mq.toml` and output the configuration as JSON.

### Test PR Generation (Dry Run)

```bash
# This will show what it would do without actually creating PRs
./mq generate --gh-token=$GH_TOKEN --trunk-token=$TRUNK_TOKEN --dry-run
```

### Test Housekeeping

```bash
./mq housekeeping --gh-token=$GH_TOKEN --trunk-token=$TRUNK_TOKEN
```

### Test Upload Targets (for parallelqueue mode)

```bash
# Create a test GitHub JSON file
echo '{"repository": {"name": "mergequeue", "owner": {"login": "merge-demo"}}}' > /tmp/github.json

./mq upload-targets --github-json=/tmp/github.json --trunk-token=$TRUNK_TOKEN
```

### Test Simulation

```bash
./mq test-sim --trunk-token=$TRUNK_TOKEN
```

## 4. Available Commands

Based on the workflows, the `mq` tool supports:

- `mq config` - Display configuration from `.config/mq.toml`
- `mq generate` - Generate pull requests
- `mq housekeeping` - Clean up old branches/PRs
- `mq upload-targets` - Upload impacted targets (for parallelqueue mode)
- `mq test-sim` - Simulate test runs

## 5. Configuration File

The tool reads from `.config/mq.toml`. Make sure it exists and is configured correctly:

```bash
cat .config/mq.toml
```

## 6. Troubleshooting

- **Permission denied**: Make sure `mq` is executable: `chmod +x mq`
- **Token errors**: Verify your tokens are set correctly: `echo $TRUNK_TOKEN`
- **Config errors**: Check that `.config/mq.toml` exists and is valid TOML
- **Network errors**: Ensure you can reach `api.trunk.io` and `api.github.com`

## 7. Example Full Test

```bash
# 1. Download and setup
curl -L -o mq.tar.gz https://github.com/trunk-io/mergequeue-tool/releases/latest/download/mq-$(uname -m)-unknown-linux-gnu.tar.gz
tar -xzf mq.tar.gz
chmod +x mq

# 2. Set tokens
export TRUNK_TOKEN="your-token"
export GH_TOKEN="your-token"

# 3. Test config
./mq config

# 4. Test (without actually creating PRs - add --dry-run if supported)
./mq generate --gh-token=$GH_TOKEN --trunk-token=$TRUNK_TOKEN
```
