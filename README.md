# Label IQ

Label IQ is an AI-powered platform that automates **CFIA (Canadian Food Inspection Agency) food label compliance reviews**. Upload food label images, and the system extracts structured data using Google Document AI, validates it against Canadian regulations using 14 specialized compliance agents, and generates a detailed compliance report.

## What It Does

1. **Upload** food label images (front, back, nutrition panel, etc.)
2. **Extract** text and structured fields using Google Document AI (OCR + custom extraction)
3. **Analyze** the extracted data against CFIA regulations using 14 AI agents:
   - **LLM agents** (Google Gemini) evaluate subjective rules — common name, bilingual requirements, ingredients, date marking, country of origin, irradiation, front-of-pack symbol, and claim tags
   - **Rule-based detectors** check quantitative rules — nutrition facts rounding, sweeteners, supplements, additives, allergens/gluten, and health claims
4. **Generate** a compliance report with pass/fail/needs-review results, regulatory citations, and supporting evidence
5. **Export** professional DOCX reports for offline sharing

## Key Features

- **Project Management** — Organize analyses into projects with tags and descriptions
- **Batch Analysis** — Upload and analyze multiple label images simultaneously
- **Real-time Monitoring** — Track analysis progress (Queued → Extracting → Compliance → Done)
- **Compliance Scoring** — Visual donut chart showing overall compliance percentage
- **Inline Editing** — Manually override AI results with reviewer comments
- **DOCX Export** — Download formatted reports for regulatory submissions
- **Bilingual Support** — Full EN/FR validation with automatic translation (RELABEL mode)
- **Event-Driven Architecture** — Scales horizontally on Google Cloud Run with Pub/Sub fan-out

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Vite, TailwindCSS, Radix UI, TanStack React Query |
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Database** | PostgreSQL (Cloud SQL) |
| **AI/ML** | Google Document AI, Google Gemini, Vertex AI Search |
| **Cloud** | Google Cloud Run, Cloud Storage, Pub/Sub, Eventarc, Cloud Translation |
| **Reports** | python-docx for DOCX generation |

## Project Structure

```
Label-IQ-experiments/
├── api/
│   └── main.py                     # FastAPI app — all REST endpoints
├── core/
│   ├── orchestrator.py             # Pipeline orchestration (extract → comply → assemble)
│   ├── processor.py                # Image preprocessing + Document AI calls
│   ├── db.py                       # PostgreSQL database manager
│   ├── pubsub.py                   # Google Pub/Sub messaging
│   ├── translate_fields.py         # EN/FR translation for RELABEL mode
│   └── report_generator_docx.py    # DOCX report generation
├── compliance/
│   ├── base_agent.py               # Abstract base class for LLM agents
│   ├── attributes_orchestrator.py  # Orchestrates all 14 agents
│   ├── group_executor.py           # Runs agent groups (identity/content/tables)
│   ├── questions.json              # CFIA compliance checklist
│   ├── agents/                     # LLM-based compliance agents
│   ├── nutrition_facts/            # NFT rounding rules auditor
│   ├── sweeteners/                 # Sweetener detection
│   ├── supplements_table/          # Supplement detection
│   ├── additive/                   # Food additive detection (661 items)
│   ├── allergens_gluten/           # Allergen/gluten detection
│   ├── health_claims/              # Health claims validation
│   └── claim_tags/                 # Claim tag evaluation (Natural, Kosher, etc.)
├── frontend/
│   ├── client/src/
│   │   ├── pages/                  # Dashboard, project view, login
│   │   ├── components/             # UI components (upload, results tables, report editor)
│   │   ├── api.ts                  # API client + TypeScript types
│   │   ├── lib/                    # Auth context, query client, utils
│   │   └── hooks/                  # Custom hooks (report edits, feedback)
│   ├── server/                     # Express.js server
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── architecture.md             # System design & data flow documentation
│   └── architecture-audit.md       # Architecture audit with known issues
├── Dockerfile                      # Backend container
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
└── README.md
```

## Getting Started (Local Development)

### Prerequisites

- **Python 3.12+**
- **Node.js 20+** and npm
- **PostgreSQL** (local instance or Cloud SQL with proxy)
- **Google Cloud Platform** project with the following APIs enabled:
  - Document AI
  - Cloud Storage
  - Cloud Translation
  - Vertex AI Search (Discovery Engine)
- **GCP Service Account** key with access to the above APIs
- **Google Gemini API key** (or OpenAI API key as fallback)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Label-IQ-experiments
```

### 2. Backend Setup

```bash
# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# ---- GCS Buckets ----
IN_BUCKET=your-project-id-label-in
OUT_BUCKET=your-project-id-label-out

# ---- Document AI ----
DOCAI_PROJECT=your-gcp-project-id
DOCAI_LOCATION=us
DOCAI_PROCESSOR_ID=your-docai-processor-id

# ---- Vertex AI Search ----
VS_PROJECT=your-gcp-project-id
VS_LOCATION=global
VS_DATASTORE_ID=your-datastore-id
VS_SERVING_CONFIG=default_search

# ---- Translation ----
TRANSLATE_PROJECT=your-gcp-project-id
TRANSLATE_LOCATION=global

# ---- Database (PostgreSQL) ----
DB_HOST=localhost
DB_PORT=5432
DB_NAME=foodlabel
DB_USER=postgres
DB_PASSWORD=your-password

# ---- AI Models ----
GOOGLE_API_KEY=your-gemini-api-key
# OR
OPENAI_API_KEY=your-openai-api-key

# ---- Evidence Provider ----
CFIA_EVIDENCE_PROVIDER=vertex_search   # or chatgpt_search
```

Make sure your GCP credentials are available:

```bash
# Option A: Set the credentials file path
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Option B: Use gcloud CLI authentication
gcloud auth application-default login
```

### 4. Set Up the Database

Create a PostgreSQL database:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE foodlabel;
```

The application automatically creates all required tables on first startup.

### 5. Set Up GCS Buckets

Create two Cloud Storage buckets in your GCP project:

```bash
gsutil mb -l us-central1 gs://your-project-id-label-in
gsutil mb -l us-central1 gs://your-project-id-label-out
```

### 6. Start the Backend

```bash
uvicorn api.main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`. You can verify it's running:

```bash
curl http://localhost:8000/api/healthz
# {"ok": true}
```

### 7. Frontend Setup

```bash
cd frontend

# Install Node.js dependencies
npm install

# Start the development server
npm run dev:client
```

The frontend will be available at `http://localhost:5000` and automatically proxies API requests to `http://localhost:8000`.

### 8. Open the Application

Navigate to `http://localhost:5000` in your browser. The development environment uses mock authentication, so you can sign in immediately.

**Workflow:**
1. Click **"Sign in with Google"** (mock auth in dev mode)
2. Create a new project from the dashboard
3. Go to the **Files** tab and upload label images
4. Monitor progress in the **Analysis** tab
5. View results in the **Reports** tab once processing is complete

## Cloud Deployment

### Backend (Cloud Run)

```bash
gcloud run deploy label-compliance \
  --source . \
  --region us-central1 \
  --project your-project-id
```

### Frontend (Cloud Run)

```bash
cd frontend
gcloud run deploy web \
  --region us-central1 \
  --source . \
  --allow-unauthenticated \
  --set-env-vars API_BASE="https://your-backend-url.run.app/api"
```

### Update Backend CORS

```bash
gcloud run services update label-compliance \
  --region us-central1 \
  --update-env-vars "CORS_ORIGINS=https://your-frontend-url.run.app"
```

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/healthz` | Health check |
| `GET` | `/api/v1/projects` | List all projects |
| `POST` | `/api/v1/projects` | Create a project |
| `GET` | `/api/v1/projects/:id` | Get project details |
| `PUT` | `/api/v1/projects/:id` | Update a project |
| `DELETE` | `/api/v1/projects/:id` | Delete a project |
| `GET` | `/api/v1/projects/:id/analyses` | List project analyses |
| `POST` | `/api/v1/jobs` | Upload images and create a compliance job |
| `GET` | `/api/v1/jobs/:id` | Get job status |
| `GET` | `/api/v1/jobs/:id/report` | Get compliance report (JSON) |
| `GET` | `/api/v1/jobs/:id/images` | List uploaded images |
| `GET` | `/api/v1/jobs/:id/images/:i` | Get a specific image |
| `POST` | `/api/v1/jobs/:id/save-edits` | Save manual report edits |
| `GET` | `/api/v1/jobs/:id/download-docx` | Download DOCX report |

For the full system design, data flow diagrams, and database schema, see [docs/architecture.md](docs/architecture.md).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `IN_BUCKET` | Yes | GCS bucket for uploaded images |
| `OUT_BUCKET` | Yes | GCS bucket for reports and job status |
| `DOCAI_PROJECT` | Yes | GCP project ID for Document AI |
| `DOCAI_LOCATION` | Yes | Document AI location (e.g., `us`) |
| `DOCAI_PROCESSOR_ID` | Yes | Custom Document AI processor ID |
| `VS_PROJECT` | Yes | GCP project for Vertex AI Search |
| `VS_DATASTORE_ID` | Yes | Vertex AI Search datastore ID |
| `DB_HOST` | Yes | PostgreSQL host |
| `DB_PORT` | Yes | PostgreSQL port |
| `DB_NAME` | Yes | PostgreSQL database name |
| `DB_USER` | Yes | PostgreSQL user |
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `GOOGLE_API_KEY` | Yes | Google Gemini API key |
| `TRANSLATE_PROJECT` | For RELABEL | GCP project for Cloud Translation |
| `OPENAI_API_KEY` | Optional | OpenAI API key (fallback LLM) |
| `CORS_ORIGINS` | Production | Comma-separated allowed origins (default: `*`) |
| `CFIA_EVIDENCE_PROVIDER` | Optional | `vertex_search` or `chatgpt_search` |
