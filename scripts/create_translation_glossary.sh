#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Need PROJECT_ID}"
: "${GLOSSARY_BUCKET:=gs://${PROJECT_ID}-translate-glossary}"
: "${LOCATION:=global}"
: "${GLOSSARY_ID:=cfia-glossary-enfr}"

gsutil cp glossary/cfia_glossary.csv ${GLOSSARY_BUCKET}/glossaries/cfia_glossary.csv

gcloud alpha translation glossaries create "$GLOSSARY_ID" \
  --location="$LOCATION" \
  --input-uri=${GLOSSARY_BUCKET}/glossaries/cfia_glossary.csv \
  --language-codes=en,fr