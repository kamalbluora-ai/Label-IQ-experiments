#!/usr/bin/env node
/**
 * Extracts <strong> elements per rules from Canadian Standards of Identity (Volumes 1–8):
 * - exclude <strong> that contains an <i>
 * - strong text must contain >= 1 alphabet [A-Za-z]
 * - for each kept <strong>, take its parent <p> and sibling <ul>
 * - store as array of { common_name_with_def, source }
 */

import * as cheerio from "cheerio";
import fs from "fs";

const BASE_URL =
  "https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference/canadian-standards-identity-volume-";

function cleanText(s) {
  return (s || "")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

async function fetchAndExtract(url, out, seen) {
  const res = await fetch(url, {
    headers: {
      "user-agent":
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
      accept: "text/html,application/xhtml+xml",
    },
  });

  if (!res.ok) {
    console.error(`⚠️ Failed: ${url} (${res.status})`);
    return;
  }

  const html = await res.text();
  const $ = cheerio.load(html);

  $("strong").each((_, el) => {
    const strong = $(el);

    // Exclude <strong> containing <i>
    if (strong.find("i").length > 0) return;

    const strongText = cleanText(strong.text());
    if (!/[A-Za-z]/.test(strongText)) return;

    const p = strong.closest("p");
    if (!p.length) return;

    let ul = p.next("ul");

    const pText = cleanText(p.text());
    let ulText = "";
    if (ul.length) ulText = cleanText(ul.text());

    const value = cleanText(`${pText}\n${ulText}`);
    if (!value) return;

    if (seen.has(value)) return;
    seen.add(value);

    out.push({
      common_name_with_def: value,
      source: url,
    });
  });
}

async function main() {
  const out = [];
  const seen = new Set();

  // Volumes 1 → 8
  for (let i = 1; i <= 8; i++) {
    const url = `${BASE_URL}${i}`;
    console.log(`Processing: ${url}`);
    await fetchAndExtract(url, out, seen);
  }

  // process.stdout.write(JSON.stringify(out, null, 2) + "\n");
  fs.writeFileSync(
    "csi_common_names.json",
    JSON.stringify(out, null, 2),
    "utf8"
  );

  console.log(`Wrote ${out.length} records to csi_common_names.json`);

}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
