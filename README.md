# CFIA Label Compliance App (Cloud Run + DocAI + Vertex AI Search + Translation)

This project processes food label images (phone photos or scans) to:
- Extract structured label fields using **Document AI Custom Extractor**
- Ground rules and citations from CFIA pages using **Vertex AI Search** (Discovery Engine API)
- Run a CFIA checklist-aligned checks matrix
- Optionally translate foreign labels (Polish, Simplified Chinese, Korean) to EN/FR with **Cloud Translation Advanced + glossary**

## Two modes
- `AS_IS`: evaluate the label as printed (strict on-pack EN/FR)
- `RELABEL`: generate proposed EN/FR relabel content via translation, and return `relabel_plan`

## Where to start
Open `project_and_cloud_setup.md` and follow the steps end-to-end.

## Local dev
1) Create a virtualenv, install deps
2) Copy `.env.example` to `.env` and fill in values
3) Run:
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

Note: Local dev uses Application Default Credentials, so run `gcloud auth application-default login`.
