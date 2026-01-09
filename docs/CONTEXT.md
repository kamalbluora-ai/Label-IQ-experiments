# Project context (CFIA Label Compliance App)

## Goal
Build a production-ready Google Cloud app that evaluates Canadian food label compliance using:
- Document AI Custom Extractor for structured field extraction from phone photos / scanned label images.
- Vertex AI Search (website content datastore) over CFIA pages (especially the CFIA "Food labelling requirements checklist") for grounded retrieval and citations.
- Cloud Translation (Advanced) with a glossary to translate foreign-language labels (Polish, Simplified Chinese, Korean) into EN/FR for a relabel plan.

## Two orchestration modes
1) AS_IS mode:
- Evaluate the label exactly as printed.
- Enforce mandatory bilingual (EN/FR) for consumer prepackaged foods except dealer name/address (exception).
- Output verdict + issues with CFIA citations (grounded snippets).

2) RELABEL mode:
- First extract source fields (including *_foreign variants).
- Translate foreign fields -> EN + FR using Translation Advanced + glossary.
- Output:
  - As-is verdict + issues
  - Proposed EN/FR relabel content (relabel_plan), keyed by base field (ingredients_list, contains_statement, etc.)
- Mark generated translations as machine-generated; human review required for high-risk fields (allergens).

## Entity schema (Document AI Custom Extractor)
Panels:
- panel_pdp, panel_ingredients, panel_nutrition, panel_dates, panel_address, panel_fop

Fields (EN/FR + foreign where applicable):
- common_name_en, common_name_fr, common_name_foreign
- net_quantity_value, net_quantity_unit_symbol, net_quantity_unit_words_en, net_quantity_unit_words_fr, net_quantity_full_text
- ingredients_list_en, ingredients_list_fr, ingredients_list_foreign
- contains_statement_en, contains_statement_fr, contains_statement_foreign
- cross_contamination_statement_en, cross_contamination_statement_fr, cross_contamination_statement_foreign
- phenylalanine_statement_en, phenylalanine_statement_fr, phenylalanine_statement_foreign
- dealer_name, dealer_address
- importer_statement_en, importer_statement_fr, importer_statement_foreign
- best_before_en, best_before_fr, best_before_foreign
- packaged_on_en, packaged_on_fr, packaged_on_foreign
- expiration_date_en, expiration_date_fr, expiration_date_foreign
- storage_instructions_en, storage_instructions_fr, storage_instructions_foreign
- lot_code
- nft_title_en, nft_title_fr, nft_title_foreign
- nft_serving_size_en, nft_serving_size_fr, nft_serving_size_foreign
- nft_calories
- nft_text_block, nft_text_block_foreign
- nft_table (optional structured table)
- fop_symbol_present, fop_symbol_text_en, fop_symbol_text_fr
- irradiation_statement_en, irradiation_statement_fr, irradiation_statement_foreign, irradiation_symbol_present
- sweetener_equivalence_statement_en, sweetener_equivalence_statement_fr, sweetener_equivalence_statement_foreign
- country_of_origin_statement_en, country_of_origin_statement_fr, country_of_origin_statement_foreign

## Current implementation notes
- The app stores job status and reports in OUT_BUCKET as JSON.
- Eventarc triggers Cloud Run on object finalize in IN_BUCKET.
- Retrieval is done via Discovery Engine SearchServiceClient using the CFIA datastore and simple query templates per checklist section.
- Translation runs only in RELABEL mode and adds fields like: ingredients_list_en_generated, ingredients_list_fr_generated etc.

## Improvements (future)
- Improve bbox extraction from DocAI entities to support "on PDP", "end of ingredients list", font prominence checks.
- Add Quebec Bill 96 prominence checks as separate optional mode (out of current scope).
- Add structured NFT validator and FOP threshold logic.
- Add a UI (React) and a human review workflow (Firestore + approval).
