"""
Test DocAI Output - Simple script to get raw DocAI extraction results
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

from core.processor import run_docai_custom_extractor
from core.orchestrator import merge_label_facts

load_dotenv()

# Config
sample_dir = Path("sample_files/ex1")
front_img = sample_dir / "front.png"
back_img = sample_dir / "back.png"

# Get env vars
project_id = os.environ["DOCAI_PROJECT"]
location = os.environ["DOCAI_LOCATION"]
processor_id = os.environ["DOCAI_PROCESSOR_ID"]

print("Extracting front image...")
front_facts = run_docai_custom_extractor(
    project_id=project_id,
    location=location,
    processor_id=processor_id,
    file_bytes=front_img.read_bytes(),
    mime_type="image/png"
)

print("Extracting back image...")
back_facts = run_docai_custom_extractor(
    project_id=project_id,
    location=location,
    processor_id=processor_id,
    file_bytes=back_img.read_bytes(),
    mime_type="image/png"
)

print("Merging...")
merged = merge_label_facts([front_facts, back_facts])

# Save to JSON
output_file = Path("docai_output.json")
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)

print(f"✓ Saved to {output_file}")
