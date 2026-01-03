# Label-IQ Backend Architecture

## Overview

Label-IQ is a **CFIA (Canadian Food Inspection Agency) Food Label Compliance Checker** that processes food label images and validates them against Canadian food labelling regulations.

## High-Level Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   Frontend  │────▶│  FastAPI    │────▶│  GCS Bucket  │────▶│  Orchestrator  │
│  (Upload)   │     │  /v1/jobs   │     │  (IN_BUCKET) │     │  (Processing)  │
└─────────────┘     └─────────────┘     └──────────────┘     └────────────────┘
                                                                      │
                    ┌─────────────────────────────────────────────────┘
                    ▼
        ┌───────────────────────────────────────────────────────────────┐
        │                     PROCESSING PIPELINE                        │
        │  ┌────────────┐   ┌────────────┐   ┌─────────────────────────┐│
        │  │ Preprocess │──▶│  Doc AI    │──▶│ Mode Detection          ││
        │  │ (Denoise/  │   │ Extraction │   │ (AS_IS vs RELABEL)      ││
        │  │  Deskew)   │   │            │   │                         ││
        │  └────────────┘   └────────────┘   └─────────────────────────┘│
        │                                              │                 │
        │         ┌────────────────────────────────────┴───────┐        │
        │         ▼                                            ▼        │
        │  ┌──────────────┐                         ┌──────────────────┐│
        │  │ AS_IS Mode   │                         │ RELABEL Mode     ││
        │  │ (No transl.) │                         │ (Translation)    ││
        │  └──────────────┘                         └──────────────────┘│
        │         │                                            │        │
        │         └────────────────────┬───────────────────────┘        │
        │                              ▼                                │
        │                   ┌─────────────────────┐                     │
        │                   │  Evidence Retrieval │                     │
        │                   │  (Vertex AI Search  │                     │
        │                   │   or ChatGPT Web)   │                     │
        │                   └─────────────────────┘                     │
        │                              │                                │
        │                              ▼                                │
        │                   ┌─────────────────────┐                     │
        │                   │  Compliance Checks  │                     │
        │                   │  (CFIA Checklist)   │                     │
        │                   └─────────────────────┘                     │
        │                              │                                │
        └──────────────────────────────┼────────────────────────────────┘
                                       ▼
                            ┌─────────────────────┐
                            │  GCS OUT_BUCKET     │
                            │  - jobs/{id}.json   │
                            │  - reports/{id}.json│
                            └─────────────────────┘
```

---

## Core Modules

### 1. `main.py` - FastAPI Entry Point

**Purpose:** API endpoints only, delegates business logic to orchestrator.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Health check |
| `/v1/jobs` | POST | Upload images, create job, returns `job_id` |
| `/v1/jobs/{job_id}` | GET | Get job status from `OUT_BUCKET/jobs/{job_id}.json` |
| `/v1/jobs/{job_id}/report` | GET | Get compliance report from `OUT_BUCKET/reports/{job_id}.json` |
| `/` | POST | Eventarc webhook (triggered by GCS upload of job.json) |

**Job Creation Flow (`POST /v1/jobs`):**
1. Accept multipart form with image files + optional `product_metadata`
2. Upload images to `IN_BUCKET/incoming/{job_id}/image_N.ext`
3. Create manifest at `IN_BUCKET/incoming/{job_id}/job.json`
4. Return `{job_id, status: "QUEUED", images: N}`

---

### 2. `orchestrator.py` - Business Logic

**Purpose:** Coordinates the entire compliance pipeline.

**Key Function: `process_manifest(bucket, manifest)`**

```python
# Flow:
1. Download images from GCS IN_BUCKET
2. Preprocess each image (denoise, deskew)
3. Run DocAI Custom Extractor → extract label_facts
4. Merge facts from multiple images
5. Detect mode (AS_IS or RELABEL based on foreign language fields)
6. If RELABEL: translate foreign fields to EN/FR
7. Get CFIA evidence (Vertex AI Search or ChatGPT)
8. Run compliance checks against CFIA checklist
9. Write report to OUT_BUCKET/reports/{job_id}.json
10. Update job status to DONE in OUT_BUCKET/jobs/{job_id}.json
```

**Mode Detection:**
- Checks for presence of `*_foreign` fields (e.g., `common_name_foreign`, `ingredients_list_foreign`)
- If found → `RELABEL` (needs translation to EN/FR)
- If not → `AS_IS` (evaluate as-is)

**Evidence Provider (configurable via `CFIA_EVIDENCE_PROVIDER` env var):**
- `"chatgpt_search"` (default): Uses OpenAI ChatGPT with web search
- `"vertex_search"`: Uses Google Vertex AI Search / Discovery Engine

---

### 3. `processor.py` - Image Processing & DocAI

**Purpose:** Image preprocessing and Document AI extraction.

**Functions:**

| Function | Description |
|----------|-------------|
| `preprocess_image_bytes(img_bytes)` | Denoise + deskew phone photos/scans |
| `run_docai_custom_extractor(...)` | Call Document AI Custom Extractor, returns normalized fields |

**DocAI Output Structure:**
```python
{
    "text": "...",           # Full OCR text (capped at 30k chars)
    "fields": {              # Best entity per type
        "common_name_en": {"text": "...", "confidence": 0.95, "bbox": None},
        "ingredients_list_en": {"text": "...", "confidence": 0.92, "bbox": None},
        ...
    },
    "fields_all": {          # All candidates per type
        "common_name_en": [{"text": "...", "confidence": 0.95}, ...],
        ...
    },
    "panels": {              # Detected panels (PDP, ingredients, nutrition, etc.)
        "panel_pdp": {"text": "...", "confidence": 0.88},
        ...
    },
    "translated": {}         # Filled by translate_fields.py in RELABEL mode
}
```

**Panel Types Detected:**
- `panel_pdp` (Principal Display Panel)
- `panel_ingredients`
- `panel_nutrition`
- `panel_dates`
- `panel_address`
- `panel_fop` (Front-of-Package symbol)

---

### 4. `translate_fields.py` - Translation Service

**Purpose:** Translate foreign language label fields to EN and FR for RELABEL mode.

**Supported Source Languages:**
- Polish (`pl`)
- Korean (`ko`)
- Simplified Chinese (`zh-Hans`)

**Translation Map (foreign → base field):**
```
common_name_foreign        → common_name
ingredients_list_foreign   → ingredients_list
contains_statement_foreign → contains_statement
nft_text_block_foreign     → nft_text_block
... (16 field mappings total)
```

**Output:**
- Adds `translated[base_key] = {src_lang, en, fr}`
- Adds convenience fields `{base_key}_en_generated`, `{base_key}_fr_generated`

---

### 5. `checks.py` - Compliance Checks

**Purpose:** Run CFIA checklist validation against extracted label facts.

**Check Categories:**
| Category | Check Codes |
|----------|-------------|
| Common Name | `COMMON_NAME_MISSING`, `COMMON_NAME_BILINGUAL` |
| Net Quantity | `NET_QUANTITY_MISSING`, `NET_QUANTITY_UNIT_WORDS_BILINGUAL` |
| Ingredients | `INGREDIENTS_LIST_MISSING`, `INGREDIENTS_BILINGUAL` |
| Allergens | `CONTAINS_BILINGUAL`, `CROSS_CONTAM_BILINGUAL` |
| Dealer Info | `DEALER_INFO_MISSING`, `IMPORTED_BY_MISSING` |
| Dates | `BEST_BEFORE_MISSING`, `BEST_BEFORE_BILINGUAL` |
| Nutrition Facts | `NFT_MISSING`, `NFT_NOT_DETECTED` |
| FOP Symbol | `FOP_NOT_EVALUATED` |

**Severity Levels:** `fail`, `needs_review`, `pass`

**Output:**
```python
{
    "verdict": "PASS" | "FAIL" | "NEEDS_REVIEW",
    "issues": [...],
    "mode": "AS_IS" | "RELABEL",
    "relabel_plan": {...}  # Only for RELABEL mode
}
```

---

### 6. Evidence Retrieval Modules

**`vertex_search.py`** - Vertex AI Search / Discovery Engine
- Queries CFIA datastore with checklist-specific queries
- Returns snippets with source URLs

**`chatgpt_search.py`** - ChatGPT Web Search Agent
- Uses OpenAI GPT-4 with web search capability
- Queries official CFIA sources for compliance rules
- Returns structured rules with citations

---

## GCS Storage Structure

### IN_BUCKET (Input)
```
incoming/{job_id}/
    ├── image_0.jpg
    ├── image_1.jpg
    └── job.json         # Manifest
```

### OUT_BUCKET (Output)
```
jobs/{job_id}.json       # Job status (QUEUED, PROCESSING, DONE, FAILED)
reports/{job_id}.json    # Full compliance report
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `IN_BUCKET` | ✅ | GCS bucket for incoming images |
| `OUT_BUCKET` | ✅ | GCS bucket for results |
| `DOCAI_PROJECT` | ✅ | GCP project for Document AI |
| `DOCAI_LOCATION` | ✅ | DocAI processor location (us) |
| `DOCAI_PROCESSOR_ID` | ✅ | Custom extractor processor ID |
| `VS_PROJECT` | ⚠️ | Vertex AI Search project (for vertex_search provider) |
| `VS_DATASTORE_ID` | ⚠️ | Vertex AI Search datastore ID |
| `TRANSLATE_PROJECT` | ⚠️ | For RELABEL mode translation |
| `TRANSLATE_GLOSSARY_ID` | ❌ | Optional translation glossary |
| `OPENAI_API_KEY` | ⚠️ | For chatgpt_search provider |
| `CFIA_EVIDENCE_PROVIDER` | ❌ | `"chatgpt_search"` (default) or `"vertex_search"` |

---

## API Request/Response Examples

### Create Job
```http
POST /v1/jobs
Content-Type: multipart/form-data

files: [image1.jpg, image2.jpg]
product_metadata: {"product_name": "Granola Bar"}
```

**Response:**
```json
{
    "job_id": "abc-123-def",
    "status": "QUEUED",
    "images": 2
}
```

### Get Job Status
```http
GET /v1/jobs/abc-123-def
```

**Response:**
```json
{
    "status": "DONE",
    "mode": "AS_IS",
    "report_path": "gs://bucket-out/reports/abc-123-def.json"
}
```

### Get Report
```http
GET /v1/jobs/abc-123-def/report
```

**Response:**
```json
{
    "job_id": "abc-123-def",
    "created_at": "2026-01-03T10:00:00Z",
    "mode": "AS_IS",
    "source_images": ["gs://bucket-in/incoming/abc-123-def/image_0.jpg"],
    "label_facts": {...},
    "results": {
        "verdict": "NEEDS_REVIEW",
        "issues": [...]
    },
    "cfia_evidence": {...}
}
```

---

## Frontend Integration Points

The frontend should use:
- `POST /v1/jobs` - Upload images and create job
- `GET /v1/jobs/{job_id}` - Poll for job completion
- `GET /v1/jobs/{job_id}/report` - Fetch final compliance report

**No "projects" concept exists in the backend** - the frontend's project layer is purely a UI organization feature that wraps around the backend's job-based workflow.
