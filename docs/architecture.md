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
         ┌──────────────────────────────────────────────────────────────────┐
         │                    AttributeOrchestrator                          │
         │                 (parallel via asyncio.gather)                     │
         ├──────────────────────────────────────────────────────────────────┤
         │  LLM Agents (async):                                             │
         │  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐           │
         │  │CommonName│ │Ingredients│ │  Date    │ │   FOP    │           │
         │  │  Agent   │ │  Agent    │ │ Marking  │ │  Symbol  │           │
         │  └──────────┘ └───────────┘ └──────────┘ └──────────┘           │
         │  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐           │
         │  │Bilingual │ │Irradiation│ │ Country  │ │ Claim Tag│           │
         │  │  Agent   │ │  Agent    │ │  Origin  │ │  Agent   │           │
         │  └──────────┘ └───────────┘ └──────────┘ └──────────┘           │
         │                                                                  │
         │  Sync Detectors (via asyncio.to_thread):                         │
         │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
         │  │   NFT    │ │Sweetener │ │Supplement│ │ Additive │           │
         │  │ Auditor  │ │ Detector │ │ Detector │ │ Detector │           │
         │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
         └──────────────────────────────────────────────────────────────────┘
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
| `IngredientsAgent` | `compliance/agents/ingredients.py` | async | Validates ingredient list compliance |
| `DateMarkingAgent` | `compliance/agents/date_marking.py` | async | Validates date marking (best before, expiry) |
| `FOPSymbolAgent` | `compliance/agents/fop_symbol.py` | async | Validates Front-of-Pack nutrition symbol |
| `BilingualAgent` | `compliance/agents/bilingual.py` | async | Validates bilingual labeling requirements |
| `IrradiationAgent` | `compliance/agents/irradiation.py` | async | Validates irradiation labeling |
| `CountryOriginAgent` | `compliance/agents/country_origin.py` | async | Validates country of origin declarations |
| `ClaimTagAgent` | `compliance/claim_tags/claim_tag_agent.py` | async | Evaluates claim tags (Natural, Kosher, Halal, Homemade/Artisan, Organic). **Guardrail:** only triggers if `claim_tag_type` field is not empty |
| `NFTAuditor` | `compliance/nutrition_facts/auditor.py` | sync | Audits nutrient values against CFIA rounding rules |
| `detect_sweeteners` | `compliance/sweeteners/detector.py` | sync | Detects sweeteners, classifies by category |
| `detect_supplements` | `compliance/supplements_table/detector.py` | sync | Detects vitamins, minerals, amino acids in NFT |
| `detect_additives` | `compliance/additive/detector.py` | sync | Detects 661 CFIA-permitted additives (14 categories) |

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

### 7. Supplement Detection Module

**Location:** `compliance/supplements_table/`

**Categories:** Amino Acid, Bioactive, Vitamin, Mineral, Other

**Output:**
```json
{"detected": [{"name": "iron", "category": "Mineral", "source": "nft"}], "has_supplements": true}
```

---

### 8. Additive Detection Module

**Location:** `compliance/additive/`

**Categories (14):** Anticaking, Bleaching, Colouring, Emulsifier, Enzyme, Firming, Glazing, pH Adjusting, Preservative, Sequestering, Starch Modifier, Yeast Food, Carrier Solvent

**Source:** CFIA Lists of Permitted Food Additives (661 total)

**Output:**
```json
{"detected": [{"name": "lecithin", "category": "Preservative", "source": "ingredients"}], "has_additives": true}
```

---

### 9. Claim Tag Module

**Location:** `compliance/claim_tags/`

**Files:**
| File | Purpose |
|------|---------|
| `claim_tag_rules.json` | Rules for 5 claim types (Nature/Natural, Kosher, Halal, Homemade/Artisan, Organic) |
| `claim_tag_agent.py` | LLM agent that evaluates claims against rules using 3 DocAI fields |
| `claim_tag_models.py` | Pydantic models (`ClaimTagResult`, `ClaimTagEvaluation`) |

**Input Fields:** `claim_tag_type`, `ingredients_list_en`, `nft_table_en`

**Guardrail:** Only triggered when `claim_tag_type` is not empty.

**Output:** All results return `NEEDS_REVIEW` status with AI reasoning.
```json
{
  "claims_detected": [{
    "claim_type": "Nature / Natural",
    "claim_text_found": "NATURALLY FLAVORED",
    "certification_body": null,
    "status": "NEEDS_REVIEW",
    "ai_reason": "Contains BHT (Preservative) and Artificial Flavor...",
    "rule_violations": ["Contains artificial additives"],
    "supporting_evidence": ["BHT (Preservative)", "Natural And Artificial Flavor"]
  }],
  "summary": "Natural claim detected with violations"
}
```

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
    "ingredients": {...},
    "date_marking": {...},
    "fop_symbol": {...},
    "bilingual": {...},
    "irradiation": {...},
    "country_origin": {...},
    "claim_tag": {...},
    "nutrition_facts": {"nutrient_audits": [...], "cross_field_audits": [...]},
    "sweeteners": {"detected": [...], "has_quantity_sweeteners": false},
    "supplements": {"detected": [...], "has_supplements": true},
    "additives": {"detected": [...], "has_additives": true}
  }
}
```
