import os
import sys
import json
from pathlib import Path

# Add core to sys.path
core_dir = Path(__file__).parent / "core"
sys.path.append(str(core_dir))

from orchestrator import split_image_bytes, merge_label_facts, guess_mime
from processor import run_docai_custom_extractor

# Config
DOCAI_PROJECT = os.environ.get("DOCAI_PROJECT")
DOCAI_LOCATION = os.environ.get("DOCAI_LOCATION")
DOCAI_PROCESSOR_ID = os.environ.get("DOCAI_PROCESSOR_ID")

def process_local_images():
    base_path = Path("sample_files/ex1")
    images = [
        {"name": "front.jpg", "tag": "front"},
        {"name": "back.jpg", "tag": "back"}
    ]
    
    all_facts = []
    
    for img_info in images:
        path = base_path / img_info["name"]
        print(f"Processing {path} (Tag: {img_info['tag']})...")
        
        with open(path, "rb") as f:
            img_bytes = f.read()
            
        mime_type = guess_mime(img_info["name"])
        
        if img_info["tag"] == "front":
            print("  - Splitting 'front' image...")
            panels = split_image_bytes(img_bytes)
            if panels:
                for panel_name, panel_bytes in panels:
                    print(f"  - Extracting split panel: {panel_name}")
                    facts = run_docai_custom_extractor(
                        project_id=DOCAI_PROJECT,
                        location=DOCAI_LOCATION,
                        processor_id=DOCAI_PROCESSOR_ID,
                        file_bytes=panel_bytes,
                        mime_type=mime_type
                    )
                    all_facts.append(facts)
            else:
                print("  - Split failed, processing as whole.")
                facts = run_docai_custom_extractor(
                    project_id=DOCAI_PROJECT,
                    location=DOCAI_LOCATION,
                    processor_id=DOCAI_PROCESSOR_ID,
                    file_bytes=img_bytes,
                    mime_type=mime_type
                )
                all_facts.append(facts)
        else:
            print("  - Processing as whole image.")
            facts = run_docai_custom_extractor(
                project_id=DOCAI_PROJECT,
                location=DOCAI_LOCATION,
                processor_id=DOCAI_PROCESSOR_ID,
                file_bytes=img_bytes,
                mime_type=mime_type
            )
            all_facts.append(facts)
            
    print("Merging results...")
    merged = merge_label_facts(all_facts)
    
    output_file = "test_split_output.json"
    with open(output_file, "w") as f:
        json.dump(merged, f, indent=2)
        
    print(f"Done. Output saved to {output_file}")
    print("Merged Fields:", list(merged.get("fields", {}).keys()))

if __name__ == "__main__":
    process_local_images()
