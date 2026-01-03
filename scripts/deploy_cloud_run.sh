#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Need PROJECT_ID}"
: "${REGION:=us-central1}"
: "${SERVICE_NAME:=label-compliance}"
: "${SA_EMAIL:?Need SA_EMAIL}"

: "${DOCAI_LOCATION:=us}"
: "${DOCAI_PROCESSOR_ID:?Need DOCAI_PROCESSOR_ID}"
: "${VS_DATASTORE_ID:?Need VS_DATASTORE_ID}"

gcloud config set project "$PROJECT_ID"

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --service-account "$SA_EMAIL" \
  --no-allow-unauthenticated \
  --set-env-vars IN_BUCKET=${PROJECT_ID}-label-in,OUT_BUCKET=${PROJECT_ID}-label-out,\
DOCAI_PROJECT=${PROJECT_ID},DOCAI_LOCATION=${DOCAI_LOCATION},DOCAI_PROCESSOR_ID=${DOCAI_PROCESSOR_ID},\
VS_PROJECT=${PROJECT_ID},VS_LOCATION=global,VS_DATASTORE_ID=${VS_DATASTORE_ID},VS_SERVING_CONFIG=default_search,\
TRANSLATE_PROJECT=${PROJECT_ID},TRANSLATE_LOCATION=global,TRANSLATE_GLOSSARY_ID=cfia-glossary-enfr