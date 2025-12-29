# Nutrition Attribute Pipeline Architecture

## Seed URL
`https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html`

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     OFFLINE (One-Time Ingestion)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. CRAWL ──► 2. CLEAN ──► 3. LLM CLASSIFIER                  │
│                                    │                            │
│                         ┌──────────┴──────────┐                 │
│                         ▼                     ▼                 │
│                   STRUCTURED              UNSTRUCTURED          │
│                   (Rules DB)              (Vector Store)        │
│                         │                     │                 │
│                   if/elif/else           Chunk → Embed          │
│                      logic                    │                 │
│                         │                     ▼                 │
│                         └───────┬─────────pgvector              │
│                                 │                               │
└─────────────────────────────────┼───────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────┐
│                     RUNTIME (Per Label Check)                   │
├─────────────────────────────────┼───────────────────────────────┤
│                                 │                               │
│   Input Label ─────► 4. STRUCTURED RULE CHECK                  │
│                              │                                  │
│                      Pass/Fail Results                          │
│                              │                                  │
│                      5. RAG QUERY (if needed)                  │
│                         │                                       │
│                   Retrieve → Augment → Generate                 │
│                              │                                  │
│                      6. FINAL COMPLIANCE REPORT                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step Details

### 1. Crawl
| Item | Value |
|------|-------|
| Seed URL | Front-of-package nutrition symbol guide |
| Depth | Single page + linked pages (1 level) |
| Output | Raw HTML per page |

**URL Filtering (Deterministic - No LLM):**

| Keep ✅ | Skip ❌ |
|---------|---------|
| `canada.ca/...food...` | External domains |
| `inspection.canada.ca/...` | `/fr/` (French duplicates) |
| `health-canada/...` | `/login`, `/feedback` |
| Paths with `/labelling/`, `/nutrition/` | `#footnote`, `.pdf` |
| Links: "requirements", "exemptions" | Links: "Report a problem" |

### 2. Clean

**Input:** `nutrition_raw_crawl.json` (raw HTML)

**Steps:**
| Step | Action | Purpose |
|------|--------|---------|
| 1 | Parse HTML | Convert to DOM (BeautifulSoup) |
| 2 | Remove nav | Strip `<header>`, `<footer>`, `<nav>`, breadcrumbs |
| 3 | Remove TOC | Strip "On this page" sections |
| 4 | Remove noise | Strip footnotes, feedback forms, language toggles |
| 5 | Extract headings | Keep `<h1>`→`<h6>` hierarchy |
| 6 | Extract tables | Keep tables as structured data (rules often here) |
| 7 | Extract text | Get clean text from `<main>` or content area |
| 8 | Normalize | Collapse whitespace, fix encoding |

**Output:** `nutrition_cleaned_data.json`
```json
{
  "url": "...",
  "title": "...",
  "headings": ["[H1] Title", "[H2] Section"],
  "tables": [{"headers": [...], "rows": [...]}],
  "clean_text": "..."
}
```

### 3. LLM Classifier
Classify each section as:

| Type | Criteria | Example |
|------|----------|---------|
| **Structured** | Has thresholds, conditions, if-then logic | "If saturated fat ≥ 15% DV → show symbol" |
| **Unstructured** | Explanatory, examples, rationale | "This threshold was chosen because..." |

### 4. Structured Rules → Rules DB
- Extract into JSON schema:
```json
{
  "rule_id": "fop_sat_fat",
  "nutrient": "saturated_fat",
  "threshold": 15,
  "unit": "percent_dv",
  "action": "show_fop_symbol"
}
```
- Validation = direct if/elif/else code

### 5. Unstructured Content → Vector Store
- Chunk: 500-1000 tokens, 200 token overlap
- Embed: OpenAI `text-embedding-3-small`
- Store: Supabase pgvector
- Use: RAG for "why", edge cases, exemptions

### 6. Runtime Hybrid Check
```
1. Run structured rules → Pass/Fail per rule
2. If ambiguous or explanation needed:
   - Query vector store for relevant context
   - Augment with retrieved chunks
   - Generate explanation via LLM
3. Output: Compliance report with citations
```

---

## File Structure
```
nutrition_attribute/
├── ARCHITECTURE.md             # This file
├── crawl.py                    # Step 1
├── clean.py                    # Step 2
├── classify.py                 # Step 3
├── rules_db.json               # Structured rules output
├── embed_and_load.py           # Step 5
└── check_label.py              # Runtime checker
```

---

## Next Steps
1. [ ] Implement crawl.py for seed URL
2. [ ] Implement clean.py with noise removal
3. [ ] Implement classify.py (LLM-based)
4. [ ] Extract structured rules to rules_db.json
5. [ ] Chunk & embed unstructured content
6. [ ] Build runtime checker with hybrid approach
