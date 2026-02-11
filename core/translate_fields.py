from typing import Dict, Any, Optional
from google.cloud import translate_v3 as translate

# Map foreign extracted fields to base logical fields.
TRANSLATE_MAP = [
    ("common_name_foreign", "common_name"),
    ("ingredients_list_foreign", "ingredients_list"),
    ("contains_statement_foreign", "contains_statement"),
    ("cross_contamination_statement_foreign", "cross_contamination_statement"),
    ("phenylalanine_statement_foreign", "phenylalanine_statement"),
    ("best_before_foreign", "best_before"),
    ("packaged_on_foreign", "packaged_on"),
    ("expiration_date_foreign", "expiration_date"),
    ("storage_instructions_foreign", "storage_instructions"),
    ("nft_title_foreign", "nft_title"),
    ("nft_serving_size_foreign", "nft_serving_size"),
    ("nft_text_block_foreign", "nft_text_block"),
    ("country_of_origin_statement_foreign", "country_of_origin_statement"),
    ("importer_statement_foreign", "importer_statement"),
    ("irradiation_statement_foreign", "irradiation_statement"),
    ("sweetener_equivalence_statement_foreign", "sweetener_equivalence_statement"),
]

# Scope languages (as requested)
SUPPORTED_FOREIGN = {"pl", "ko", "zh-Hans"}  # Polish, Korean, Simplified Chinese

def translate_foreign_fields(
    label_facts: Dict[str, Any],
    project_id: str,
    location: str = "global",
    glossary_id: Optional[str] = None,
    allow_undetected: bool = True,
) -> Dict[str, Any]:
    """Detect language per foreign field and translate to EN and FR.
    Adds:
      - label_facts['translated'][base_key] = {src_lang, en, fr}
      - convenience fields in label_facts['fields']:
          f"{base_key}_en_generated", f"{base_key}_fr_generated"
    """
    client = translate.TranslationServiceClient()
    parent = f"projects/{project_id}/locations/{location}"

    fields = label_facts.get("fields", {}) or {}
    translated = label_facts.get("translated", {}) or {}

    for foreign_key, base_key in TRANSLATE_MAP:
        src = _get_text(fields, foreign_key)
        if not src:
            continue

        src_lang = _detect_language(client, parent, src) or "und"

        # If already EN/FR, skip.
        if src_lang in ("en", "fr"):
            continue

        if (src_lang not in SUPPORTED_FOREIGN) and (src_lang != "und"):
            translated[base_key] = {
                "src_lang": src_lang,
                "en": None,
                "fr": None,
                "note": "Source language not in configured scope; manual review."
            }
            continue

        if (src_lang == "und") and not allow_undetected:
            translated[base_key] = {
                "src_lang": "und",
                "en": None,
                "fr": None,
                "note": "Language detection failed; manual review."
            }
            continue

        en = _translate_text(client, parent, src, src_lang, "en", glossary_id)
        fr = _translate_text(client, parent, src, src_lang, "fr", glossary_id)

        translated[base_key] = {"src_lang": src_lang, "en": en, "fr": fr}

        # Convenience fields used by checks.py
        fields[f"{base_key}_en_generated"] = {"text": en or "", "confidence": 1.0, "bbox": None}
        fields[f"{base_key}_fr_generated"] = {"text": fr or "", "confidence": 1.0, "bbox": None}

    label_facts["translated"] = translated
    label_facts["fields"] = fields
    return label_facts


def _get_text(fields: Dict[str, Any], key: str) -> str:
    v = fields.get(key)
    if isinstance(v, dict):
        return (v.get("text") or "").strip()
    return ""


def _detect_language(client: translate.TranslationServiceClient, parent: str, text: str) -> Optional[str]:
    resp = client.detect_language(parent=parent, content=text)
    if resp.languages:
        return resp.languages[0].language_code
    return None


def _translate_text(
    client: translate.TranslationServiceClient,
    parent: str,
    text: str,
    src_lang: str,
    tgt_lang: str,
    glossary_id: Optional[str],
) -> Optional[str]:
    glossary_config = None
    if glossary_id:
        glossary = f"{parent}/glossaries/{glossary_id}"
        glossary_config = translate.TranslateTextGlossaryConfig(glossary=glossary)

    req = translate.TranslateTextRequest(
        parent=parent,
        contents=[text],
        mime_type="text/plain",
        source_language_code=None if src_lang == "und" else src_lang,
        target_language_code=tgt_lang,
        glossary_config=glossary_config,
    )
    resp = client.translate_text(request=req)
    if resp.glossary_translations:
        return resp.glossary_translations[0].translated_text
    if resp.translations:
        return resp.translations[0].translated_text
    return None
