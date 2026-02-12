import re
from typing import List, Set
from compliance.health_claims.models import DetectedClaim, HealthClaimsDetectionResult
from compliance.health_claims.claims_db import (
    DISEASE_RISK_PHRASE_TO_CATEGORY,
    NUTRIENT_FUNCTION_PHRASE_TO_CATEGORY,
    PROBIOTIC_PHRASE_TO_CATEGORY,
    NUTRIENT_CONTENT_PHRASE_TO_CATEGORY,
    ALL_DISEASE_RISK_PHRASES,
    ALL_NUTRIENT_FUNCTION_PHRASES,
    ALL_PROBIOTIC_PHRASES,
    ALL_NUTRIENT_CONTENT_PHRASES,
)


def normalize_text(text: str) -> str:
    """Normalize text: lowercase, strip punctuation, collapse whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _match_phrases(
    normalized_text: str,
    phrases: Set[str],
    phrase_to_category: dict,
    claim_type: str,
    source: str,
) -> List[DetectedClaim]:
    """Match known phrases against normalized text using substring search."""
    detected = []
    matched_categories = set()

    # Sort longest-first so more specific patterns win
    for phrase in sorted(phrases, key=len, reverse=True):
        if phrase in normalized_text:
            category = phrase_to_category[phrase]

            # One match per category per source
            dedup_key = f"{category}:{source}"
            if dedup_key in matched_categories:
                continue
            matched_categories.add(dedup_key)

            detected.append(DetectedClaim(
                name=phrase,
                category=category,
                claim_type=claim_type,
                source=source,
            ))

    return detected


def detect_health_claims(
    health_claims_text: str = "",
    nutrient_content_text: str = "",
    nutrient_function_text: str = "",
    label_text: str = "",
) -> HealthClaimsDetectionResult:
    """
    Detect health and nutrient claims from DocAI-extracted text fields.
    Falls back to full label_text if dedicated fields are empty.
    """
    detected: List[DetectedClaim] = []
    seen = set()  # (category, claim_type) dedup across fields

    def _add_claims(claims: List[DetectedClaim]):
        for c in claims:
            key = (c.category, c.claim_type)
            if key not in seen:
                seen.add(key)
                detected.append(c)

    # 1. Check health_claims_text for disease risk reduction + probiotic
    norm_health = normalize_text(health_claims_text)
    if norm_health:
        _add_claims(_match_phrases(
            norm_health, ALL_DISEASE_RISK_PHRASES,
            DISEASE_RISK_PHRASE_TO_CATEGORY,
            "disease_risk_reduction", "health_claims",
        ))
        _add_claims(_match_phrases(
            norm_health, ALL_PROBIOTIC_PHRASES,
            PROBIOTIC_PHRASE_TO_CATEGORY,
            "probiotic", "health_claims",
        ))

    # 2. Check nutrient_content_claims_text
    norm_content = normalize_text(nutrient_content_text)
    if norm_content:
        _add_claims(_match_phrases(
            norm_content, ALL_NUTRIENT_CONTENT_PHRASES,
            NUTRIENT_CONTENT_PHRASE_TO_CATEGORY,
            "nutrient_content", "nutrient_content",
        ))

    # 3. Check nutrient_function_claims_text
    norm_function = normalize_text(nutrient_function_text)
    if norm_function:
        _add_claims(_match_phrases(
            norm_function, ALL_NUTRIENT_FUNCTION_PHRASES,
            NUTRIENT_FUNCTION_PHRASE_TO_CATEGORY,
            "nutrient_function", "nutrient_function",
        ))
        _add_claims(_match_phrases(
            norm_function, ALL_PROBIOTIC_PHRASES,
            PROBIOTIC_PHRASE_TO_CATEGORY,
            "probiotic", "nutrient_function",
        ))

    # 4. Fallback: scan full label_text if no dedicated fields found anything
    if not detected and label_text:
        norm_label = normalize_text(label_text)
        if norm_label:
            for phrases, lookup, ctype in [
                (ALL_DISEASE_RISK_PHRASES, DISEASE_RISK_PHRASE_TO_CATEGORY, "disease_risk_reduction"),
                (ALL_NUTRIENT_CONTENT_PHRASES, NUTRIENT_CONTENT_PHRASE_TO_CATEGORY, "nutrient_content"),
                (ALL_NUTRIENT_FUNCTION_PHRASES, NUTRIENT_FUNCTION_PHRASE_TO_CATEGORY, "nutrient_function"),
                (ALL_PROBIOTIC_PHRASES, PROBIOTIC_PHRASE_TO_CATEGORY, "probiotic"),
            ]:
                _add_claims(_match_phrases(norm_label, phrases, lookup, ctype, "label_text"))

    return HealthClaimsDetectionResult(
        detected=detected,
        has_health_claims=len(detected) > 0,
    )
