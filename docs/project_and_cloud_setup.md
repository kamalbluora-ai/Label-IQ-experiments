# Project & Cloud Setup (End-to-end) — US-first configuration

This guide sets up a production-ready pipeline:

**Cloud Storage (input) → Eventarc → Cloud Run (orchestrator)**
- Preprocess photo/scan
- Document AI Custom Extractor → structured fields
- Vertex AI Search (CFIA website datastore) → grounded evidence + citations
- Checks engine (CFIA checklist-aligned)
- Optional Translation Advanced + glossary (RELABEL mode)
**Outputs**: JSON reports in Cloud Storage (output bucket), retrievable via API.

---

## 0) Prereqs
- Google Cloud project with billing enabled
- `gcloud` installed and authenticated
- Roles to create: buckets, Cloud Run, Eventarc, Document AI processors, Vertex AI Search data store, Translation glossary

---

## 1) Clone/open in VS Code
1. Download and unzip this project.
2. Open the folder in VS Code.
3. Copy `.env.example` → `.env` and fill values as you create resources.

---

## 2) Enable APIs
```bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  eventarc.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  documentai.googleapis.com \
  discoveryengine.googleapis.com \
  translate.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

---

## 3) Create buckets
Choose a region close to your users. Example uses `northamerica-northeast1` (Montreal).

```bash
export PROJECT_ID=YOUR_PROJECT_ID

gsutil mb -l us-central1 gs://$PROJECT_ID-label-in
gsutil mb -l us-central1 gs://$PROJECT_ID-label-out
gsutil mb -l us-central1 gs://$PROJECT_ID-translate-glossary
```

---

## 4) Create a service account & IAM
```bash
gcloud iam service-accounts create label-compliance-sa \
  --display-name="Label compliance orchestrator"

export SA="label-compliance-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Cloud Run invoke (Eventarc calls your service)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" \
  --role="roles/run.invoker"

# Storage read/write
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" \
  --role="roles/storage.objectAdmin"

# Document AI
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" \
  --role="roles/documentai.apiUser"

# Vertex AI Search / Discovery Engine
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" \
  --role="roles/discoveryengine.viewer"

# Translation
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" \
  --role="roles/cloudtranslate.user"

# Secret Manager (optional)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 5) Create Vertex AI Search data store (CFIA grounding)

### 5.1 In Console
Go to **Vertex AI Search / Agent Builder**:
1. **Data stores** → **Create data store** → **Website content**
2. Name: `cfia-labeling-website`
3. Add CFIA URLs to seed crawling (start with the checklist page):
   - https://inspection.canada.ca/en/food-labels/labelling/industry/requirements-checklist
4. Create the data store and let indexing complete.
5. Create a **Search app** connected to this data store.

Record these values:
- VS_DATASTORE_ID
- VS_SERVING_CONFIG (often `default_search`)
- VS_LOCATION (often `global`)

Add them to `.env`.

---

## 6) Create Document AI Custom Extractor

### 6.1 In Console
Go to **Document AI** → **Workbench**:
1. Create a **Custom Extractor** processor.
2. Define the entity schema from `CONTEXT.md` (copy/paste names).
3. Upload training images and label entities.
4. Train, evaluate, and publish the processor.

> Tip: Start by labeling **panels** first (panel_pdp, panel_ingredients, panel_nutrition, panel_dates, panel_address).
> Then label the core fields: common name, net quantity, ingredients, address, NFT title/table, dates.

Record:
- DOCAI_LOCATION
- DOCAI_PROCESSOR_ID
Add them to `.env`.

---

## 7) Translation glossary (optional but recommended)

### 7.1 Upload glossary CSV
We include a starter glossary at `glossary/cfia_glossary.csv`.

```bash
gsutil cp glossary/cfia_glossary.csv gs://$PROJECT_ID-translate-glossary/glossaries/cfia_glossary.csv
```

### 7.2 Create glossary resource
```bash
gcloud alpha translation glossaries create cfia-glossary-enfr \
  --location=global \
  --input-uri=gs://$PROJECT_ID-translate-glossary/glossaries/cfia_glossary.csv \
  --language-codes=en,fr
```

Set in `.env`:
- TRANSLATE_GLOSSARY_ID=cfia-glossary-enfr

---

## 8) Deploy Cloud Run
gcloud run deploy label-compliance \
  --source . \
  --region us-central1 \
  --service-account $SA \
  --no-allow-unauthenticated \
  --set-env-vars IN_BUCKET=${PROJECT_ID}-label-in,OUT_BUCKET=${PROJECT_ID}-label-out,\
DOCAI_PROJECT=${PROJECT_ID},DOCAI_LOCATION=us,DOCAI_PROCESSOR_ID=YOUR_PROCESSOR_ID,\
VS_PROJECT=${PROJECT_ID},VS_LOCATION=global,VS_DATASTORE_ID=YOUR_DATASTORE_ID,VS_SERVING_CONFIG=default_search,\
TRANSLATE_PROJECT=${PROJECT_ID},TRANSLATE_LOCATION=global,TRANSLATE_GLOSSARY_ID=cfia-glossary-enfr
```

After deploy, note the service URL:
```bash
gcloud run services describe label-compliance --region us-central1 --format='value(status.url)'
```

---

## 9) Create Eventarc trigger (GCS → Cloud Run)
```bash
gcloud eventarc triggers create label-in-finalize   --location=northamerica-northeast1   --destination-run-service=label-compliance   --destination-run-region=northamerica-northeast1   --event-filters="type=google.cloud.storage.object.v1.finalized"   --event-filters="bucket=${PROJECT_ID}-label-in"   --service-account="$SA"
```

---

## 10) Run a test (quickstart)

### 10.1 Upload an image
Use `incoming/{job_id}/file.jpg` so the job id is derived from the path:

```bash
JOB_ID=$(python - <<'PY'
import uuid; print(uuid.uuid4())
PY
)
gsutil cp ./YOUR_LABEL.jpg gs://${PROJECT_ID}-label-in/incoming/${JOB_ID}/label.jpg
```

### 10.2 (Optional) Create a job record first to set mode/metadata
Job records live in OUT bucket at `jobs/{job_id}.json`. Create one:

```bash
cat > /tmp/job.json <<EOF
{
  "job_id": "$JOB_ID",
  "mode": "RELABEL",
  "product_metadata": {
    "imported": true,
    "bilingual_exempt": false,
    "nft_required": false
  }
}
EOF

gsutil cp /tmp/job.json gs://${PROJECT_ID}-label-out/jobs/${JOB_ID}.json
```

Now upload the label again (or upload after creating job.json). The service will read the job record and run in that mode.

### 10.3 Fetch the report
```bash
gsutil cat gs://${PROJECT_ID}-label-out/reports/${JOB_ID}.json | head -n 80
```

You should see:
- `results.mode` = AS_IS or RELABEL
- `results.verdict` and `issues[]`
- If RELABEL: `results.relabel_plan` with generated EN/FR
- `cfia_evidence` with URLs and snippets

---

## 11) Local development (optional)

### 11.1 Authenticate ADC
```bash
gcloud auth application-default login
```

### 11.2 Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# export env vars from .env (use direnv or manual export)
uvicorn app.main:app --reload --port 8080
```

Local testing (only submit job record):
- This app is event-driven; easiest local test is to call `process_one` manually or invoke the Cloud Run service with a test CloudEvent payload.

---

## 12) Using the two orchestration modes

### AS_IS mode
Set `mode=AS_IS` (default). It evaluates the label as printed.
- Foreign-only labels will typically FAIL on bilingual checks unless exempt.

### RELABEL mode
Set `mode=RELABEL`. It:
- extracts foreign fields
- translates foreign → EN/FR using Translation Advanced (+ glossary if set)
- returns `relabel_plan` with the proposed EN/FR content.

---

## 13) Document AI training tips (you will do at home)
- Photograph ~20-30 products, 3 images per product: front (PDP), ingredients, nutrition/dates.
- Label panels first, then core fields.
- Label exactly what is printed; do NOT translate during labeling.
- For foreign labels, label the *_foreign entities.

---

## 14) Security & production notes
- Keep Cloud Run private; access via IAM or API Gateway/IAP.
- Store output reports in a secure bucket with retention.
- Add human review for high-risk fields (allergens, nutrition thresholds).
- Improve bbox extraction later for PDP placement and font prominence.

