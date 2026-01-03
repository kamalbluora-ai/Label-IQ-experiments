#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Need PROJECT_ID}"
: "${REGION:=us-central1}"
: "${SERVICE_NAME:=label-compliance}"
: "${SA_EMAIL:?Need SA_EMAIL}"

gcloud eventarc triggers create label-in-finalize \
  --location="$REGION" \
  --destination-run-service="$SERVICE_NAME" \
  --destination-run-region="$REGION" \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=${PROJECT_ID}-label-in" \
  --service-account="$SA_EMAIL"
