import io
from typing import Dict, Any, List, Optional

import cv2
import numpy as np
from PIL import Image
from google.cloud import documentai_v1 as documentai

PANEL_TYPES = {
    "panel_pdp",
    "panel_ingredients",
    "panel_nutrition",
    "panel_dates",
    "panel_address",
    "panel_fop",
}

def preprocess_image_bytes(img_bytes: bytes) -> bytes:
    """Preprocess phone photos/scans: denoise + deskew + JPEG encode."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # Mild denoise (helps phone noise)
    arr = cv2.fastNlMeansDenoisingColored(arr, None, 10, 10, 7, 21)

    # Deskew
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(bw < 255))
    if coords.size > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = arr.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        arr = cv2.warpAffine(arr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    ok, out = cv2.imencode(".jpg", arr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    return out.tobytes() if ok else img_bytes


def run_docai_custom_extractor(
    project_id: str,
    location: str,
    processor_id: str,
    file_bytes: bytes,
    mime_type: str,
) -> Dict[str, Any]:
    """Run Document AI Custom Extractor and normalize outputs to:
      - fields: best entity per type
      - fields_all: all candidates per type
      - panels: best panel entity per panel type
    """
    client = documentai.DocumentProcessorServiceClient()
    name = client.processor_path(project_id, location, processor_id)

    raw_document = documentai.RawDocument(content=file_bytes, mime_type=mime_type)
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)
    doc = result.document

    print("entities:", len(doc.entities))
    print("pages:", len(doc.pages))
    if doc.entities:
        e0 = doc.entities[0]
        print("entity has page_anchor:", hasattr(e0, "page_anchor") and bool(getattr(e0.page_anchor, "page_refs", None)))
    if doc.pages and doc.pages[0].lines:
        print("line bbox exists:", bool(doc.pages[0].lines[0].layout.bounding_poly))


    fields_all: Dict[str, List[Dict[str, Any]]] = {}
    panels: Dict[str, Dict[str, Any]] = {}

    for e in doc.entities:
        etype = (e.type_ or "").strip()
        text = (e.mention_text or "").strip()
        conf = float(e.confidence or 0.0)

        if not etype or not text:
            continue

        item = {"text": text, "confidence": conf, "bbox": None}

        if etype in PANEL_TYPES:
            cur = panels.get(etype)
            if (cur is None) or (conf > cur.get("confidence", 0.0)):
                panels[etype] = item
            continue

        fields_all.setdefault(etype, []).append(item)

    fields: Dict[str, Any] = {}
    for k, arr in fields_all.items():
        best = max(arr, key=lambda x: x.get("confidence", 0.0))
        fields[k] = best

    return {
        "text": doc.text[:30000],
        "fields": fields,
        "fields_all": fields_all,
        "panels": panels,
        "translated": {},  # filled by translate_fields in RELABEL mode
    }
