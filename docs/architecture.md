# Label-IQ Backend Architecture

## Overview

Label-IQ is a **CFIA (Canadian Food Inspection Agency) Food Label Compliance Checker** that processes food label images and validates them against Canadian food labelling regulations.

## High-Level Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Frontend   │────▶│  FastAPI    │────▶│ GCS IN_BUCKET│
│  (Upload)   │     │  /v1/jobs   │     │ (raw images) │
└─────────────┘     └─────────────┘     └──────────────┘
                                               │
                                               ▼
                              ┌─────────────────────────────┐
                              │        PROCESSING           │
                              ├─────────────────────────────┤
                              │ 1. Check cache              │
                              │ 2. Split front images       │
                              │ 3. DocAI (OCR + extraction) │
                              │ 4. Merge facts              │
                              │ 5. Mode Detection (AS_IS)   │
                              └─────────────────────────────┘
                                               │
                                               ▼
                    ┌──────────────────────────────────────────────┐
                    │           AttributeOrchestrator              │
                    │          (parallel via asyncio.gather)       │
                    ├──────────────────────────────────────────────┤
                    │  ┌────────────┐ ┌────────────┐ ┌───────────┐ │
                    │  │CommonName  │ │ NFTAuditor │ │ Sweetener │ │
                    │  │  Agent     │ │            │ │ Detector  │ │
                    │  └────────────┘ └────────────┘ └───────────┘ │
                    └──────────────────────────────────────────────┘
                                               │
                                               ▼
                              ┌─────────────────────────────┐
                              │      GCS OUT_BUCKET         │
                              │  - jobs/{id}.json           │
                              │  - reports/{id}.json        │
                              └─────────────────────────────┘
```

---

## Core Modules

### 1. `main.py` - FastAPI Entry Point

**Purpose:** API endpoints only, delegates business logic to orchestrator.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Health check |
| `/v1/jobs` | POST | Upload images, create job, returns `job_id` |
| `/v1/jobs/{job_id}` | GET | Get job status |
| `/v1/jobs/{job_id}/report` | GET | Get compliance report |

---

### 2. `orchestrator.py` - Business Logic

**Purpose:** Coordinates the entire compliance pipeline.

**Flow:**
1. Download images from GCS IN_BUCKET
2. Check cache for existing label_facts
3. If cache miss:
   - Split "front" tagged images width-wise (left/right panels)
   - Run DocAI Custom Extractor → extract label_facts
   - Merge facts from multiple images/panels
4. Detect mode (AS_IS or RELABEL)
5. If RELABEL: translate foreign fields to EN/FR
6. Run `AttributeOrchestrator.evaluate_sync()` for compliance checks
7. Write report to OUT_BUCKET

---

### 3. `AttributeOrchestrator` - Compliance Evaluation

**Location:** `compliance/attributes_orchestrator.py`

**Purpose:** Orchestrates all compliance checks in parallel using `asyncio.gather()`.

| Component | Location | Type | Function |
|-----------|----------|------|----------|
| `CommonNameAgent` | `compliance/agents/common_name.py` | async | Validates common name EN/FR |
| `NFTAuditor` | `compliance/nutrition_facts/auditor.py` | sync | Audits nutrient values against CFIA rounding rules |
| `detect_sweeteners` | `compliance/sweeteners/detector.py` | sync | Detects sweeteners, classifies by category |

**Sweetener Detection Features:**
- Categorizes by type (Polyol, Non-Nutritive, Saccharin, Steviol Glycoside, Monk Fruit)
- Flags `needs_review` if `with_quantity` sweetener has no quantity declared

---

### 4. `processor.py` - Image Processing & DocAI

**Functions:**

| Function | Description |
|----------|-------------|
| `preprocess_image_bytes(img_bytes)` | Denoise + deskew |
| `run_docai_custom_extractor(...)` | Document AI extraction |

**DocAI Output Structure:**
```python
{
    "text": "...",           # Full OCR text
    "fields": {},            # Best entity per type
    "fields_all": {},        # All candidates per type
    "panels": {},            # Detected panels
    "translated": {}         # For RELABEL mode
}
```

---

### 5. Sweetener Detection Module

**Location:** `compliance/sweeteners/`

**Files:**
| File | Purpose |
|------|---------|
| `constants.py` | Sweetener categories (Polyol, Non-Nutritive, etc.) |
| `detector.py` | Detection logic with category lookup |
| `models.py` | Pydantic models for output |

**Output Example:**
```json
{
  "detected": [{
    "name": "sorbitol",
    "sweetener_category": "Polyol",
    "category": "with_quantity",
    "quantity": "5g",
    "source": "ingredients",
    "status": null
  }],
  "has_quantity_sweeteners": true,
  "has_no_quantity_sweeteners": false
}
```

---

### 6. Nutrition Facts Auditor

**Location:** `compliance/nutrition_facts/`

**Files:**
| File | Purpose |
|------|---------|
| `auditor.py` | NFTAuditor class with rounding rules |
| `integration.py` | Map DocAI output to nutrient inputs |
| `cross_check_rules.py` | Cross-field validations |

**Checks:**
- Individual nutrient rounding compliance
- Calorie calculation consistency
- Saturated + Trans fat %DV
- Fat/carb component consistency

---

## GCS Storage Structure

### IN_BUCKET
```
incoming/{job_id}/
    ├── front.jpg
    ├── back.jpg
    └── job.json
```

### OUT_BUCKET
```
jobs/{job_id}.json       # Job status
reports/{job_id}.json    # Compliance report
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `IN_BUCKET` | ✅ | GCS input bucket |
| `OUT_BUCKET` | ✅ | GCS output bucket |
| `DOCAI_PROJECT` | ✅ | GCP project for DocAI |
| `DOCAI_LOCATION` | ✅ | DocAI location (us) |
| `DOCAI_PROCESSOR_ID` | ✅ | Custom extractor ID |
| `TRANSLATE_PROJECT` | ⚠️ | For RELABEL mode |
| `OPENAI_API_KEY` | ⚠️ | For LLM agents |

---

## API Examples

### Create Job
```http
POST /v1/jobs
Content-Type: multipart/form-data

files: [front.jpg, back.jpg]
tags: ["front", "back"]
product_metadata: {"food_type": "snack"}
```

### Get Report
```json
{
  "job_id": "abc-123",
  "results": {
    "common_name": {...},
    "nutrition_facts": {
      "nutrient_audits": [...],
      "cross_field_audits": [...]
    },
    "sweeteners": {
      "detected": [...],
      "has_quantity_sweeteners": false
    }
  }
}
```
