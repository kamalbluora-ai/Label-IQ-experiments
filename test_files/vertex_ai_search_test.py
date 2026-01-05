# Runs the retrieve evidence based on the env variable CFIA_EVIDENCE_PROVIDER

import json, os
from core.orchestrator import process_manifest
manifest = json.load(open("sample_files/ex1/job.json"))
report = process_manifest(bucket=os.environ["IN_BUCKET"], manifest=manifest)
print(report["report_path"], report["results"].get("verdict"))

