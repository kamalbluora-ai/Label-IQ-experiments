# Label-IQ System Architecture

> **Last updated:** 2026-02-13
> **Branch:** `rules-implementation`

---

## Table of Contents

1. [System Design](#1-system-design)
   - [Overview](#11-overview)
   - [Infrastructure](#12-infrastructure)
   - [Architecture Diagram](#13-architecture-diagram)
   - [API Endpoints](#14-api-endpoints)
   - [Compliance Agents](#15-compliance-agents)
   - [Database Schema](#16-database-schema)
   - [GCS Storage Layout](#17-gcs-storage-layout)
   - [Core Modules](#18-core-modules)
2. [Data Flow](#2-data-flow)
   - [Job Lifecycle](#21-job-lifecycle)
   - [Phase 1 — Image Extraction](#22-phase-1--image-extraction)
   - [Phase 2 — Compliance Checking](#23-phase-2--compliance-checking)
   - [Phase 3 — Report Assembly](#24-phase-3--report-assembly)
   - [Frontend Polling and Report Display](#25-frontend-polling-and-report-display)
   - [Deduplication and Atomicity](#26-deduplication-and-atomicity)
   - [Local vs Cloud Run Execution](#27-local-vs-cloud-run-execution)

---

## 1. System Design

### 1.1 Overview

Label-IQ is a **CFIA (Canadian Food Inspection Agency) food label compliance platform** that processes food label images, extracts structured data using Google Document AI, and validates the data against Canadian food labelling regulations using 14 AI-powered compliance agents.

The system follows a **3-phase, event-driven pipeline**:

| Phase | Name | What Happens |
|-------|------|-------------|
| **Phase 1** | Extraction | Document AI extracts text and fields from uploaded label images |
| **Phase 2** | Compliance | 14 agents in 3 groups evaluate the extracted data against CFIA rules |
| **Phase 3** | Assembly | All agent results are combined into a final compliance report |

### 1.2 Infrastructure

The system is deployed on **Google Cloud Run** as 2 containers:

| Container | Tech Stack | Purpose |
|-----------|-----------|---------|
| **backend** | Python 3.12, FastAPI, Uvicorn | Document AI extraction + Compliance orchestration |
| **web** | Node 20, React 19, Express | Frontend UI |

**Supporting GCP services:**

| Service | Purpose |
|---------|---------|
| **Cloud SQL (PostgreSQL)** | Job state, compliance results, projects, analyses |
| **Google Cloud Storage** | Image uploads, extracted facts, compliance reports |
| **Google Pub/Sub** | Fan-out/fan-in messaging for parallel agent execution |
| **Eventarc** | Triggers Phase 1 when `job.json` is uploaded to GCS |
| **Document AI** | OCR and custom field extraction from label images |
| **Google Cloud Translation** | EN/FR translation for RELABEL mode |
| **Vertex AI Search** | Retrieves CFIA regulatory evidence for agent context |

### 1.3 Architecture Diagram

```
                    ┌───────────────────────────────────────────────┐
                    │              FRONTEND (web)                    │
                    │         React 19 + Express.js                  │
                    │           Cloud Run :8080                      │
                    │                                               │
                    │  Pages:                                       │
                    │    /login         → Authentication             │
                    │    /dashboard     → Project listing            │
                    │    /project/:id   → File upload, analysis,     │
                    │                     reports (multi-tab)        │
                    └──────────────┬────────────────────────────────┘
                                   │ REST API calls
                                   │ (polling for status)
                                   v
                    ┌───────────────────────────────────────────────┐
                    │          BACKEND (backend)                     │
                    │        FastAPI + Uvicorn :8080                 │
                    │              Cloud Run                         │
                    │                                               │
                    │  ┌─ Health ─────────────────────────────────┐ │
                    │  │ GET  /api/healthz                        │ │
                    │  └─────────────────────────────────────────-┘ │
                    │  ┌─ Projects ───────────────────────────────┐ │
                    │  │ GET    /api/v1/projects                  │ │
                    │  │ POST   /api/v1/projects                  │ │
                    │  │ GET    /api/v1/projects/:id              │ │
                    │  │ PUT    /api/v1/projects/:id              │ │
                    │  │ DELETE /api/v1/projects/:id              │ │
                    │  │ GET    /api/v1/projects/:id/analyses     │ │
                    │  └─────────────────────────────────────────-┘ │
                    │  ┌─ Jobs ───────────────────────────────────┐ │
                    │  │ POST /api/v1/jobs             (upload)   │ │
                    │  │ GET  /api/v1/jobs/:id         (status)   │ │
                    │  │ GET  /api/v1/jobs/:id/report  (report)   │ │
                    │  │ GET  /api/v1/jobs/:id/images  (list)     │ │
                    │  │ GET  /api/v1/jobs/:id/images/:i (proxy)  │ │
                    │  │ POST /api/v1/jobs/:id/save-edits         │ │
                    │  │ GET  /api/v1/jobs/:id/download-docx      │ │
                    │  └─────────────────────────────────────────-┘ │
                    │  ┌─ Event Webhooks ─────────────────────────┐ │
                    │  │ POST /api/eventarc            (Phase 1)  │ │
                    │  │ POST /api/compliance/execute  (Phase 2)  │ │
                    │  │ POST /api/compliance/finalize (Phase 3)  │ │
                    │  └─────────────────────────────────────────-┘ │
                    └──────┬──────────┬──────────┬─────────────────┘
                           │          │          │
             ┌─────────────┘          │          └──────────────┐
             v                        v                         v
     ┌──────────────┐    ┌────────────────────┐    ┌──────────────────┐
     │  GCS Buckets │    │  Cloud Pub/Sub     │    │  Cloud SQL       │
     │              │    │                    │    │  (PostgreSQL)    │
     │  IN_BUCKET:  │    │ compliance-fan-out │    │                  │
     │   incoming/  │    │   → triggers       │    │  Tables:         │
     │   facts/     │    │     Phase 2 x3     │    │  - jobs          │
     │              │    │                    │    │  - docai_        │
     │  OUT_BUCKET: │    │ compliance-group-  │    │    extractions   │
     │   jobs/      │    │   done             │    │  - label_facts   │
     │   reports/   │    │   → triggers       │    │  - compliance_   │
     │              │    │     Phase 3        │    │    results       │
     └──────┬───────┘    └────────────────────┘    │  - projects      │
            │                                       │  - analyses      │
            v                                       └──────────────────┘
     ┌──────────────┐
     │  Eventarc    │
     │  (GCS        │
     │   trigger)   │
     │  → triggers  │
     │    Phase 1   │
     └──────────────┘
```

### 1.4 API Endpoints

#### Health Check

| Method | Endpoint | Trigger | Description |
|--------|----------|---------|-------------|
| `GET` | `/api/healthz` | Frontend / Cloud Run liveness probe | Returns `{"ok": true}` |

#### Project Management

| Method | Endpoint | Trigger | Description |
|--------|----------|---------|-------------|
| `GET` | `/api/v1/projects` | Dashboard page load | List all projects |
| `POST` | `/api/v1/projects` | "Create Project" dialog | Create a new project. Body: `{name, description?, tags?}` |
| `GET` | `/api/v1/projects/{project_id}` | Project view page load | Get single project details |
| `PUT` | `/api/v1/projects/{project_id}` | "Edit Project" dialog | Update project name, description, tags |
| `DELETE` | `/api/v1/projects/{project_id}` | Delete button on project card | Delete project and all its analyses |
| `GET` | `/api/v1/projects/{project_id}/analyses` | Project view → Analysis tab | List all analyses (jobs) for a project |

#### Job Management (Core Pipeline)

| Method | Endpoint | Trigger | Description |
|--------|----------|---------|-------------|
| `POST` | `/api/v1/jobs` | File upload in Files tab | Upload images, create GCS manifest, return `job_id`. Form data: `files[]`, `product_metadata?`, `tags?`, `project_id?` |
| `GET` | `/api/v1/jobs/{job_id}` | Frontend polling (every 2-5s) | Get current job status. Returns `{job_id, status, created_at, mode}` |
| `GET` | `/api/v1/jobs/{job_id}/report` | Reports tab when status is DONE | Retrieve the completed compliance report JSON from GCS |
| `GET` | `/api/v1/jobs/{job_id}/images` | Reports tab, image gallery | List uploaded images for the job |
| `GET` | `/api/v1/jobs/{job_id}/images/{index}` | Image gallery click | Proxy a specific image from GCS (avoids exposing signed URLs) |
| `POST` | `/api/v1/jobs/{job_id}/save-edits` | "Save" button in report editor | Persist manual tag/comment edits to the report JSON and regenerate the DOCX |
| `GET` | `/api/v1/jobs/{job_id}/download-docx` | "Download Report" button | Generate and stream a DOCX compliance report |

#### Event Webhooks (Cloud Run internal)

| Method | Endpoint | Trigger | Description |
|--------|----------|---------|-------------|
| `POST` | `/api/eventarc` | **Eventarc** — fires when `incoming/{job_id}/job.json` is written to `IN_BUCKET` | Kicks off Phase 1: downloads images, runs Document AI, merges facts, publishes fan-out messages |
| `POST` | `/api/compliance/execute` | **Pub/Sub** `compliance-fan-out` subscription (×3, one per group) | Executes a single compliance agent group (`identity`, `content`, or `tables`). Publishes to `compliance-group-done` when finished |
| `POST` | `/api/compliance/finalize` | **Pub/Sub** `compliance-group-done` subscription (×3, one per group completion) | Atomically increments completion counter. Last group to arrive triggers Phase 3: report assembly |

### 1.5 Compliance Agents

The system runs **14 compliance agents** organized into **3 execution groups**. LLM agents call **Google Gemini** for structured evaluation. Rule-based detectors run pure Python logic.

#### Group: Identity

| Agent | Type | File | What It Checks |
|-------|------|------|----------------|
| CommonNameAgent | LLM | `compliance/agents/common_name.py` | Common name present in EN and FR |
| BilingualAgent | LLM | `compliance/agents/bilingual.py` | All mandatory fields in both official languages |
| CountryOriginAgent | LLM | `compliance/agents/country_origin.py` | Country of origin declaration |
| IrradiationAgent | LLM | `compliance/agents/irradiation.py` | Irradiation symbol and statement if applicable |

#### Group: Content

| Agent | Type | File | What It Checks |
|-------|------|------|----------------|
| IngredientsAgent | LLM | `compliance/agents/ingredients.py` | Ingredient list format, order, allergen declarations |
| DateMarkingAgent | LLM | `compliance/agents/date_marking.py` | Best-before, expiry, and packaging dates |
| FOPSymbolAgent | LLM | `compliance/agents/fop_symbol.py` | Front-of-pack nutrition symbol compliance |
| ClaimTagAgent | LLM | `compliance/claim_tags/claim_tag_agent.py` | Claim tags (Natural, Kosher, Halal, Organic, Homemade) — only runs if `claim_tag_type` is present |
| AllergenGlutenDetector | Rule | `compliance/allergens_gluten/detector.py` | Allergen and gluten declarations |

#### Group: Tables

| Agent | Type | File | What It Checks |
|-------|------|------|----------------|
| NutritionFactsAuditor | Rule | `compliance/nutrition_facts/auditor.py` | NFT rounding rules, calorie calculations, %DV cross-checks |
| SweetenersDetector | Rule | `compliance/sweeteners/detector.py` | Sweetener identification and categorization (Polyol, Non-Nutritive, etc.) |
| SupplementsDetector | Rule | `compliance/supplements_table/detector.py` | Vitamins, minerals, amino acids in the NFT |
| AdditivesDetector | Rule | `compliance/additive/detector.py` | 661 CFIA-permitted food additives across 14 categories |
| HealthClaimsDetector | Rule | `compliance/health_claims/detector.py` | Health and nutrient content claims validation |

### 1.6 Database Schema

The system uses **PostgreSQL** (Cloud SQL) with the following tables:

#### `jobs` — Job state and completion tracking

```sql
CREATE TABLE jobs (
    job_id          TEXT PRIMARY KEY,
    status          TEXT,       -- QUEUED | EXTRACTING | EXTRACTED | COMPLIANCE_STARTED | PROCESSING | DONE | FAILED
    mode            TEXT,       -- AS_IS | RELABEL
    total_groups    INTEGER DEFAULT 3,
    completed_groups INTEGER DEFAULT 0,
    facts_path      TEXT,
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP
);
```

#### `docai_extractions` — Raw Document AI outputs per image

```sql
CREATE TABLE docai_extractions (
    id          SERIAL PRIMARY KEY,
    job_id      TEXT REFERENCES jobs(job_id),
    image_tag   TEXT,       -- front, back, left_panel, right_panel
    raw_json    TEXT,       -- Full Document AI JSON response
    created_at  TIMESTAMP
);
```

#### `label_facts` — Merged and translated facts

```sql
CREATE TABLE label_facts (
    job_id                  TEXT PRIMARY KEY REFERENCES jobs(job_id),
    merged_facts_json       TEXT,   -- Consolidated from all images
    translated_facts_json   TEXT,   -- For RELABEL mode
    updated_at              TIMESTAMP
);
```

#### `compliance_results` — Agent results and deduplication markers

```sql
CREATE TABLE compliance_results (
    id          SERIAL PRIMARY KEY,
    job_id      TEXT REFERENCES jobs(job_id),
    agent_name  TEXT,       -- e.g., common_name, __group_exec__:identity, __group_done__:tables
    status      TEXT,       -- RUNNING | DONE | ERROR
    result_json TEXT,
    created_at  TIMESTAMP,
    UNIQUE(job_id, agent_name)
);
```

#### `projects` — Project grouping

```sql
CREATE TABLE projects (
    id          TEXT PRIMARY KEY,   -- project-{uuid}
    name        TEXT NOT NULL,
    description TEXT,
    tags        TEXT,               -- JSON array
    created_at  TIMESTAMP,
    updated_at  TIMESTAMP
);
```

#### `analyses` — Links projects to jobs

```sql
CREATE TABLE analyses (
    id          TEXT PRIMARY KEY,   -- same as job_id
    project_id  TEXT REFERENCES projects(id),
    name        TEXT NOT NULL,
    status      TEXT,               -- running | completed | failed
    progress    INTEGER,            -- 0-100
    job_id      TEXT REFERENCES jobs(job_id),
    image_names TEXT,               -- JSON array of filenames
    created_at  TIMESTAMP
);
```

### 1.7 GCS Storage Layout

#### `IN_BUCKET` (uploads)

```
incoming/{job_id}/
    ├── image_0.jpg       # Uploaded label image
    ├── image_1.jpg       # Additional image
    └── job.json          # Manifest (triggers Eventarc)
```

#### `OUT_BUCKET` (outputs)

```
jobs/{job_id}.json        # Job status (polled by frontend)
facts/{job_id}.json       # Extracted label facts (Phase 1 output)
reports/{job_id}.json     # Compliance report (Phase 3 output)
reports/{job_id}.docx     # Generated DOCX report
```

### 1.8 Core Modules

#### Backend (`/api`, `/core`, `/compliance`)

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI app, all REST endpoints, CORS, Pydantic models |
| `core/orchestrator.py` | Pipeline orchestration — extraction, compliance, report assembly |
| `core/processor.py` | Image preprocessing (OpenCV denoise/deskew) and Document AI calls |
| `core/db.py` | PostgreSQL connection pooling, all DB operations, schema init |
| `core/pubsub.py` | Pub/Sub `publish_fan_out()` and `publish_group_done()` |
| `core/translate_fields.py` | Google Translation API for RELABEL mode |
| `core/report_generator_docx.py` | DOCX report generation using python-docx |
| `compliance/base_agent.py` | Abstract base class for LLM compliance agents |
| `compliance/attributes_orchestrator.py` | Orchestrates all 14 agents concurrently |
| `compliance/group_executor.py` | Runs a specific agent group (identity/content/tables) |
| `compliance/prompt.py` | Dynamic prompt builder for Gemini calls |
| `compliance/questions.json` | CFIA compliance checklist questions |

#### Frontend (`/frontend/client/src`)

| File / Directory | Purpose |
|------------------|---------|
| `pages/dashboard.tsx` | Project listing, search, create/delete |
| `pages/project-view.tsx` | Multi-tab project interface (Files, Analysis, Reports) |
| `pages/login.tsx` | Authentication page |
| `api.ts` | API client, TypeScript types, React Query hooks |
| `components/file-upload.tsx` | Drag-and-drop image upload |
| `components/ComplianceResultsSection.tsx` | Renders agent check results with pass/fail/needs-review |
| `components/NutritionAuditTable.tsx` | NFT audit findings display |
| `components/BilingualFieldsTable.tsx` | EN/FR field comparison |
| `components/DetectionResultsTable.tsx` | Generic detection results (sweeteners, additives, etc.) |
| `components/project-tabs/reports-tab.tsx` | Report view, inline editing, DOCX export |
| `components/project-tabs/files-tab.tsx` | File management and upload trigger |
| `components/project-tabs/analysis-tab.tsx` | Job status progress indicator |
| `lib/auth-context.tsx` | Authentication context (mock mode for dev) |
| `hooks/useReportEdits.ts` | Manages report edits and syncs to API |

---

## 2. Data Flow

### 2.1 Job Lifecycle

A job transitions through the following statuses:

```
QUEUED → EXTRACTING → EXTRACTED → COMPLIANCE_STARTED → DONE
                                                      ↘ FAILED
```

| Status | Set By | Meaning |
|--------|--------|---------|
| `QUEUED` | `POST /api/v1/jobs` | Job created, images uploaded to GCS, manifest written |
| `EXTRACTING` | `POST /api/eventarc` | Phase 1 started — Document AI processing images |
| `EXTRACTED` | `POST /api/eventarc` (end) | Phase 1 complete — facts saved, fan-out published |
| `COMPLIANCE_STARTED` | `POST /api/compliance/execute` | Phase 2 started — at least one agent group running |
| `DONE` | `POST /api/compliance/finalize` | Phase 3 complete — report assembled and saved |
| `FAILED` | Any phase on error | Unrecoverable error occurred |

### 2.2 Phase 1 — Image Extraction

**Triggered by:** `POST /api/eventarc` (Eventarc fires when `incoming/{job_id}/job.json` lands in `IN_BUCKET`)

```
Eventarc detects job.json in IN_BUCKET
    │
    ▼
POST /api/eventarc
    │
    ├── 1. Idempotency check: skip if job already past QUEUED
    │
    ├── 2. Acknowledge quickly (processing runs in BackgroundTasks)
    │
    ▼
process_manifest() [runs in background]
    │
    ├── 3. Set status → EXTRACTING
    │
    ├── 4. Download images from GCS IN_BUCKET
    │
    ├── 5. Preprocess images (OpenCV denoise + deskew)
    │
    ├── 6. For "front" tagged images → split width-wise into L/R panels
    │
    ├── 7. Run Document AI Custom Extractor on each image/panel
    │      └── Extracts: common_name, ingredients_list, nft_text_block,
    │          contains_statement, claim_tag_type, panels, etc.
    │
    ├── 8. Merge facts from all images (best candidate by confidence)
    │
    ├── 9. If mode=RELABEL → translate foreign fields to EN/FR
    │      └── Uses Google Cloud Translation API
    │
    ├── 10. Save facts → GCS facts/{job_id}.json + DB label_facts table
    │
    ├── 11. Set status → EXTRACTED
    │
    └── 12. Publish 3× Pub/Sub messages to "compliance-fan-out" topic
           ├── {job_id, group: "identity", facts_path}
           ├── {job_id, group: "content",  facts_path}
           └── {job_id, group: "tables",   facts_path}
```

### 2.3 Phase 2 — Compliance Checking

**Triggered by:** `POST /api/compliance/execute` (Pub/Sub `compliance-fan-out` push subscription, 3 concurrent invocations)

```
Pub/Sub delivers fan-out message (one per group)
    │
    ▼
POST /api/compliance/execute
    │
    ├── 1. Parse Pub/Sub push body → extract job_id, group, facts_path
    │
    ├── 2. Deduplication: check __group_exec__ marker in DB
    │      └── If already claimed → return {ignored: true}
    │
    ├── 3. Claim group execution (atomic INSERT into compliance_results)
    │
    ├── 4. Set status → COMPLIANCE_STARTED (on first group)
    │
    ├── 5. Load label_facts from GCS facts/{job_id}.json
    │
    ├── 6. Execute agents for the group (concurrently within group):
    │
    │      IDENTITY GROUP:
    │      ├── CommonNameAgent.evaluate()    → Gemini LLM
    │      ├── BilingualAgent.evaluate()     → Gemini LLM
    │      ├── CountryOriginAgent.evaluate() → Gemini LLM
    │      └── IrradiationAgent.evaluate()   → Gemini LLM
    │
    │      CONTENT GROUP:
    │      ├── IngredientsAgent.evaluate()   → Gemini LLM
    │      ├── DateMarkingAgent.evaluate()   → Gemini LLM
    │      ├── FOPSymbolAgent.evaluate()     → Gemini LLM
    │      ├── ClaimTagAgent.evaluate()      → Gemini LLM (conditional)
    │      └── AllergenGlutenDetector.run()  → Rule-based
    │
    │      TABLES GROUP:
    │      ├── NutritionFactsAuditor.run()   → Rule-based
    │      ├── SweetenersDetector.run()      → Rule-based
    │      ├── SupplementsDetector.run()     → Rule-based
    │      ├── AdditivesDetector.run()       → Rule-based
    │      └── HealthClaimsDetector.run()    → Rule-based
    │
    ├── 7. Save each agent's results → DB compliance_results table
    │
    ├── 8. Mark group done → INSERT __group_done__ marker
    │
    └── 9. Publish to "compliance-group-done" topic
           └── {job_id, group}
```

**Agent execution detail:**

Each LLM agent:
1. Loads its section of questions from `questions.json`
2. Prepares input data from the extracted label facts
3. Builds a structured prompt via `compliance/prompt.py`
4. Calls Google Gemini with the prompt
5. Parses the structured JSON response: `{results: [{question_id, question, result, rationale}]}`
6. Retries up to 2 times on failure; falls back to "needs_review" for all questions

Each rule-based detector:
1. Reads specific fields from label facts (e.g., `nft_text_block`, `ingredients_list`)
2. Runs pattern matching / lookup logic against known databases
3. Returns structured results (e.g., `{detected: [...], has_sweeteners: true}`)

### 2.4 Phase 3 — Report Assembly

**Triggered by:** `POST /api/compliance/finalize` (Pub/Sub `compliance-group-done` push subscription, called 3 times — once per group completion)

```
Pub/Sub delivers group-done message
    │
    ▼
POST /api/compliance/finalize
    │
    ├── 1. Parse Pub/Sub body → extract job_id, group
    │
    ├── 2. Guard: if status already DONE → ignore (dedup)
    │
    ├── 3. Atomically increment completed_groups counter
    │      └── UPDATE jobs SET completed_groups = completed_groups + 1
    │          WHERE job_id = ? AND group NOT already counted
    │          RETURNING completed_groups, total_groups
    │
    ├── 4. If completed_groups < total_groups → return {waiting: true}
    │      └── Another invocation will handle assembly
    │
    ├── 5. ═══ ALL 3 GROUPS DONE ═══
    │
    ├── 6. Claim report finalize (prevents double assembly)
    │
    ├── 7. Load all compliance_results from DB for this job
    │
    ├── 8. Load label_facts from DB
    │
    ├── 9. Combine into final report JSON:
    │      {
    │        job_id, status: "DONE",
    │        label_facts: {...},
    │        results: {
    │          common_name:      {check_results: [...]},
    │          bilingual:        {check_results: [...]},
    │          ingredients:      {check_results: [...]},
    │          date_marking:     {check_results: [...]},
    │          ...
    │          nutrition_facts:  {nutrient_audits: [...], cross_field_audits: [...]},
    │          sweeteners:       {detected: [...], has_quantity_sweeteners: bool},
    │          supplements:      {detected: [...], has_supplements: bool},
    │          additives:        {detected: [...], has_additives: bool},
    │          allergens_gluten: {detected: [...], ...},
    │          health_claims:    {detected: [...], ...}
    │        }
    │      }
    │
    ├── 10. Save report → GCS reports/{job_id}.json
    │
    ├── 11. Generate DOCX → GCS reports/{job_id}.docx
    │
    └── 12. Set status → DONE
```

### 2.5 Frontend Polling and Report Display

```
User uploads images in Files tab
    │
    ├── POST /api/v1/jobs (multipart form with files + tags + project_id)
    │   └── Returns {job_id, status: "QUEUED"}
    │
    ▼
Frontend starts polling GET /api/v1/jobs/{job_id} every 2-5 seconds
    │
    ├── status: QUEUED           → Progress bar: ~10%
    ├── status: EXTRACTING       → Progress bar: ~30%
    ├── status: EXTRACTED        → Progress bar: ~50%
    ├── status: COMPLIANCE_STARTED → Progress bar: ~70%
    │
    ▼ status: DONE
    │
    ├── GET /api/v1/jobs/{job_id}/report → Load full compliance report
    │
    ├── Render in Reports tab:
    │   ├── Compliance score (donut chart)
    │   ├── ComplianceResultsSection → Pass/Fail/Needs Review per agent
    │   ├── NutritionAuditTable → Rounding rule violations
    │   ├── BilingualFieldsTable → EN/FR field comparison
    │   ├── DetectionResultsTable → Sweeteners, additives, supplements
    │   └── Image gallery → GET /api/v1/jobs/{job_id}/images
    │
    ├── User can edit results:
    │   └── POST /api/v1/jobs/{job_id}/save-edits → Updates JSON + regenerates DOCX
    │
    └── User can download:
        └── GET /api/v1/jobs/{job_id}/download-docx → Streams DOCX file
```

### 2.6 Deduplication and Atomicity

The event-driven architecture uses **at-least-once delivery** (Pub/Sub), so every step has deduplication guards:

| Guard | Mechanism | Prevents |
|-------|-----------|----------|
| **Job processing** | `claim_job_processing()` — atomic DB update with status check | Duplicate Eventarc deliveries from re-processing same job |
| **Group execution** | `claim_group_execution()` — `INSERT ... ON CONFLICT DO NOTHING` for `__group_exec__:{group}` marker | Same group running twice on concurrent Pub/Sub deliveries |
| **Group completion** | `__group_done__:{group}` marker — checked before incrementing counter | Double-counting a group in the completion counter |
| **Report finalize** | `claim_report_finalize()` — atomic claim in DB | Two concurrent finalize calls both building the report |
| **Eventarc idempotency** | Status check at handler entry — skips if already past `QUEUED` | Eventarc redelivery after processing started |

### 2.7 Local vs Cloud Run Execution

The system supports two execution modes:

| Aspect | Local Development | Cloud Run Production |
|--------|-------------------|----------------------|
| **Phase 1 trigger** | `BackgroundTasks` inside `POST /api/v1/jobs` | Eventarc webhook → `POST /api/eventarc` |
| **Phase 2 trigger** | Runs sequentially inside `process_manifest()` | Pub/Sub fan-out → 3× `POST /api/compliance/execute` |
| **Phase 3 trigger** | Runs at end of `process_manifest()` | Pub/Sub fan-in → `POST /api/compliance/finalize` |
| **Parallelism** | Sequential (all agents run one by one) | 3 groups run in parallel, agents within each group also parallel |
| **Detection** | `IS_CLOUD_RUN = os.environ.get("K_SERVICE") is not None` | `K_SERVICE` is automatically set by Cloud Run |
| **Database** | Direct PostgreSQL connection | Cloud SQL with connection pooling |
| **Frontend proxy** | Vite dev server proxies API calls to `:8000` | Express serves static files, `API_BASE` env var points to backend URL |

---

*Generated from architecture audit and codebase analysis — 2026-02-13*
