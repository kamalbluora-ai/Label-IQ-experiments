# Label IQ - CFIA Label Compliance Platform
Label IQ is an AI-powered platform for automating CFIA food label compliance reviews. It uses a modern full-stack architecture to process label images, check them against Canadian regulations, and generate detailed issues reports.

## System Architecture
The system consists of two main components:

1.  **Frontend (`/frontend`)**: A React/Vite web application that provides the user interface for project management, file uploads, analysis monitoring, and reporting.
2.  **Backend (`/core`)**: A FastAPI service that orchestrates the compliance pipeline.

### Core Pipeline (GCS-Based)
The backend operates on a stateless, event-driven architecture using Google Cloud Storage (GCS):
1.  **Upload:** Frontend uploads images directly to the backend -> GCS (`incoming/{job_id}/`).
2.  **Processing:** 
    *   **Document AI:** Extracts text and fields (ingredients, nutrition types, etc.) from images.
    *   **Vertex AI Search:** Retrieves relevant CFIA regulatory evidence.
    *   **Compliance Logic:** Validates extracted data against rules (e.g., bilingual requirements, net quantity formatting).
3.  **Output:** Generates a comprehensive JSON report stored in GCS (`reports/{job_id}.json`).

## Features

*   **Project Management**: Organize analyses into projects.
*   **Batch Analysis**: Upload and analyze multiple label images simultaneously.
*   **Real-time Monitoring**: Track analysis status (Queued -> Processing -> Completed) live.
*   **Detailed Reporting**: 
    *   **Visual Score**: Donut chart indicating overall compliance percentage.
    *   **Issues List**: Specific violations with severity levels (Pass, Needs Review, Fail).
    *   **Regulatory Evidence**: Direct citations from CFIA laws for every issue.
    *   **Extracted Data**: Visibility into the raw data (ingredients, dealer info) extracted by the AI.
*   **PDF Export**: Download professional compliance reports for offline sharing.

## Getting Started

### Prerequisites
*   Node.js (v18+)
*   Python 3.10+
*   Google Cloud Platform project with necessary APIs enabled (Document AI, Vertex AI, GCS, Translation).

### 1. Backend Setup (`/core`)

```bash
cd core
# Create virtual environment
python -m venv env
.\env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup for crawl4ai
crawl4ai-setup

# Configure Environment
# Copy .env.example to .env and fill in your GCP credentials/bucket info
cp .env.example .env

# Run Server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup (`/frontend`)

```bash
cd frontend
# Install dependencies
npm install

# Run Development Server
npm run dev:client
```
The frontend will run on `http://localhost:5000` (proxied to backend on port 8000).

## Environment Variables (.env for Backend)

Ensure your `core/.env` file has the following:
*   `GOOGLE_APPLICATION_CREDENTIALS`: Path to your service account JSON.
*   `IN_BUCKET`: GCS bucket for uploads.
*   `OUT_BUCKET`: GCS bucket for reports.
*   `DOCAI_PROCESSOR_ID`: ID of your Document AI processor.
*   `VS_DATASTORE_ID`: ID of your Vertex AI Search datastore.
*   `TRANSLATE_PROJECT`: GCP Project ID for translation.

## Usage Workflow

1.  **Login**: Click "Sign in with Google" (Mock authentication is enabled for dev).
2.  **Create Project**: Start a new compliance project (e.g., "Granola Bar 2024").
3.  **Upload**: Go to the **Files** tab and upload label images.
4.  **Analyze**: The system automatically starts processing upon upload.
5.  **Report**: Once complete, go to the **Final Reports** tab to view the detailed analysis and download the PDF.


# Testing commands

## Deploy Backend (from project root)
```bash
gcloud run deploy "backend" --region "us-central1" --source . --allow-unauthenticated
```

## Deploy Frontend (from frontend folder)
```bash
cd frontend
gcloud run deploy "web" --region "us-central1" --source . --allow-unauthenticated --set-env-vars API_BASE="https://YOUR_BACKEND_URL"
```

## Run Backend Locally (from project root)
```bash
uvicorn api.main:app --reload --port 8000
```

## Run Frontend Locally (from frontend folder)
```bash
cd frontend
npm run dev:client
```