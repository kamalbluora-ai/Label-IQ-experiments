#!/usr/bin/env node
/**
 * Extracts <strong> elements per rules:
 * - exclude <strong> that contains an <i>
 * - strong text must contain >= 1 alphabet [A-Za-z]
 * - for each kept <strong>, take its parent <p> and sibling <ul>
 * - store as array of { common_name_with_def: "<p text>\n<ul text>" }
 */

import * as cheerio from "cheerio";

const URL =
  "https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference/canadian-food-compositional-standards-0";

function cleanText(s) {
  return (s || "")
    .replace(/\u00a0/g, " ")          // nbsp -> space
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

async function main() {
  const res = await fetch(URL, {
    headers: {
      "user-agent":
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
      "accept": "text/html,application/xhtml+xml",
    },
  });

  if (!res.ok) {
    throw new Error(`Fetch failed: ${res.status} ${res.statusText}`);
  }

  const html = await res.text();
  const $ = cheerio.load(html);

  const out = [];
  const seen = new Set();

  $("strong").each((_, el) => {
    const strong = $(el);

    // Exclude <strong> that contains an <i>
    if (strong.find("i").length > 0) return;

    const strongText = cleanText(strong.text());
    if (!/[A-Za-z]/.test(strongText)) return;

    // Parent <p>
    const p = strong.closest("p");
    if (!p.length) return;

    // Sibling <ul> (prefer immediate next <ul>, otherwise any sibling <ul>)
    let ul = p.next("ul");
    // if (!ul.length) ul = p.siblings("ul").first();
    // if (!ul.length) return;

    const pText = cleanText(p.text());
    var ulText = ''
    if (ul.length)
        ulText = cleanText(ul.text());

    // Store combined value
    const value = cleanText(`${pText}\n${ulText}`);
    if (!value) return;

    // Optional dedupe (prevents repeats if DOM has duplicates)
    if (seen.has(value)) return;
    seen.add(value);

    out.push({ common_name_with_def: value });
  });

  process.stdout.write(JSON.stringify(out, null, 2) + "\n");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
