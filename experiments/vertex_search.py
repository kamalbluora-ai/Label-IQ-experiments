from typing import Dict, Any, List
from google.cloud import discoveryengine_v1 as discoveryengine

# Simple checklist-driven queries. In production you can map checks -> queries 1:1 for cleaner citations.
CHECKLIST_QUERIES = {
    "RULES_COMMON_NAME": "Retreive all rules from CFIA checklist applicable to common name requirements in a structured bulleted list",
    "COMMON_NAME": "Food labelling requirements checklist common name principal display panel type height 1.6 mm 0.8 mm",
    "NET_QUANTITY": "Food labelling requirements checklist net quantity declared on the PDP metric units bilingual symbols",
    "INGREDIENTS_ALLERGENS": "Food labelling requirements checklist list of ingredients allergens contains statement cross-contamination statement order",
    "BILINGUAL": "Food labelling requirements checklist bilingual requirements mandatory information English and French exception name and address",
    "DATES": "Food labelling requirements checklist best before meilleur avant packaged on empaqueté le storage instructions",
    "NUTRITION_FACTS": "Food labelling requirements checklist Nutrition Facts table exemptions available display surface 15 cm2 100 cm2",
    "FOP": "Food labelling requirements checklist front-of-package nutrition symbol location on PDP",
    "IRRADIATION": "Food labelling requirements checklist irradiation statement international symbol on PDP",
    "SWEETENERS": "Food labelling requirements checklist aspartame phenylalanine statement table-top sweetener equivalence",
    "ORIGIN": "Food labelling requirements checklist country of origin Product of",
}

def cfia_retrieve_snippets(
    project_id: str,
    location: str,
    datastore_id: str,
    serving_config: str,
    label_facts: Dict[str, Any],
    product_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    client = discoveryengine.SearchServiceClient()
    serving_config_path = client.serving_config_path(
        project=project_id,
        location=location,
        data_store=datastore_id,
        serving_config=serving_config,
    )

    evidence: Dict[str, Any] = {}
    for k, q in CHECKLIST_QUERIES.items():
        req = discoveryengine.SearchRequest(
            serving_config=serving_config_path,
            query=q,
            page_size=5,
        )
        resp = client.search(req)
        hits = []
        for r in resp.results:
            doc = r.document
            url = ""
            title = ""
            snippet = ""
            if doc.derived_struct_data:
                d = dict(doc.derived_struct_data)
                url = d.get("link", "") or d.get("url", "")
                title = d.get("title", "")
                sn = d.get("snippets")
                if isinstance(sn, object) and sn:
                    snippet = sn[0]["snippet"]
                elif isinstance(sn, str):
                    snippet = sn
            hits.append({"title": title, "url": url, "snippet": snippet})
        evidence[k] = hits
    return evidence
