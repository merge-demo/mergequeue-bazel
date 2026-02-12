#!/usr/bin/env node
/**
 * Word counter application - displays word dictionary statistics.
 * Similar to the UV wordcounter app, but implemented in Node.js for Nx.
 */

const fs = require("fs");
const path = require("path");

// Dictionary mapping folder names to their word lists
const WORD_DICT = {};

// Word list packages (similar to UV setup)
const wordPackages = [
  "alpha",
  "bravo",
  "charlie",
  "delta",
  "echo",
  "foxtrot",
  "golf",
  "hotel",
  "indigo",
  "juliet",
  "kilo",
];

// Load words from each package's .txt file
for (const pkg of wordPackages) {
  const txtPath = path.join(__dirname, "../../", pkg, `${pkg}.txt`);
  try {
    const content = fs.readFileSync(txtPath, "utf-8");
    const words = content
      .split("\n")
      .map((line) => line.trim())
      .filter((word) => word.length > 0);
    WORD_DICT[pkg] = words;
  } catch (error) {
    console.error("Error loading", pkg + ":", error.message);
    WORD_DICT[pkg] = [];
  }
}

function main() {
  console.log("Nx Word Dictionary");
  console.log("=".repeat(50));

  for (const [folder, words] of Object.entries(WORD_DICT)) {
    console.log(`${folder}: ${words.length} words`);
  }

  const totalWords = Object.values(WORD_DICT).reduce((sum, words) => sum + words.length, 0);
  console.log(`\nTotal words: ${totalWords}`);
}

if (require.main === module) {
  main();
}

module.exports = { WORD_DICT, main };
