# Turbo Workspace

This directory contains a Turbo workspace setup to demonstrate parallel queues

## Structure

- **Word packages**: `packages/alpha/`, `packages/bravo/`, `packages/charlie/`, `packages/delta/`,
  `packages/echo/`, `packages/foxtrot/`, `packages/golf/`, `packages/hotel/`, `packages/indigo/`,
  `packages/juliet/`, `packages/kilo/`
  - Each package contains a `.txt` file with words and a `package.json` configuration
- **Apps**: `apps/wordcounter/`
  - The wordcounter app displays statistics about all word packages

## Setup

To use Turbo commands, first install dependencies:

```bash
cd turbo
npm install
```

## Running the Wordcounter App

```bash
npm run wordcounter

# Or using Turbo (after installing dependencies)
npx turbo run build
```

## Project Structure

The Turbo workspace follows a similar structure to the Nx and Bazel setups:

- Each word package is a separate workspace package
- The wordcounter app consumes all word packages
- All packages are configured with `package.json` files
- Turbo manages the build pipeline and caching
