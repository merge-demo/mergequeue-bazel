# Nx Workspace

This directory contains an Nx workspace setup to demonstrate parralel queues

## Structure

- **Word packages**: `alpha/`, `bravo/`, `charlie/`, `delta/`, `echo/`, `foxtrot/`, `golf/`
  - Each package contains a `.txt` file with words and a `project.json` configuration
- **Apps**: `apps/wordcounter/`
  - The wordcounter app displays statistics about all word packages

## Setup

To use Nx commands, first install dependencies:

```bash
cd nx
npm install
```

## Running the Wordcounter App

```bash
npm run wordcounter

# Or using Nx (after installing dependencies)
npx nx run wordcounter:run
```

## Project Structure

The Nx workspace follows a similar structure to the Bazel setup:

- Each word package is a separate Nx project
- The wordcounter app consumes all word packages
- All projects are configured with `project.json` files
