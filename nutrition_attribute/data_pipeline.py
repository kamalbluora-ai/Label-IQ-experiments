"""
Nutrition Attribute Data Pipeline Orchestrator
Runs the full offline pre-RAG pipeline:
  1. Crawl   → Fetch raw HTML from curated URLs
  2. Clean   → Extract structured content from HTML
  3. Classify → Split structured rules vs unstructured content
  4. Chunk   → Split content into token-limited chunks
  5. Embed   → Generate embeddings for each chunk
  6. Store   → Save to vector database (pgvector/Supabase)

Usage:
    python data_pipeline.py              # Run full pipeline
    python data_pipeline.py --from clean # Start from clean step
    python data_pipeline.py --step crawl # Run single step
"""

import argparse
import sys
from pathlib import Path

# Pipeline steps
STEPS = ['crawl', 'clean', 'classify', 'chunk', 'embed', 'store']

# File paths
SCRIPT_DIR = Path(__file__).parent
FILES = {
    'raw': SCRIPT_DIR / 'nutrition_raw_crawl.json',
    'cleaned': SCRIPT_DIR / 'nutrition_cleaned_data.json',
    'classified': SCRIPT_DIR / 'nutrition_classified.json',
    'chunked': SCRIPT_DIR / 'nutrition_chunks.json',
    'embedded': SCRIPT_DIR / 'nutrition_embedded.json',
}


def run_crawl():
    """Step 1: Crawl URLs and save raw HTML."""
    print("\n" + "=" * 60)
    print("STEP 1: CRAWL")
    print("=" * 60)
    from nutrition_attribute_crawl import main as crawl_main
    crawl_main()
    return FILES['raw'].exists()


def run_clean():
    """Step 2: Clean raw HTML into structured data."""
    print("\n" + "=" * 60)
    print("STEP 2: CLEAN")
    print("=" * 60)
    from nutrition_attribute_clean import main as clean_main
    clean_main()
    return FILES['cleaned'].exists()


def run_classify():
    """Step 3: Classify content as structured rules or unstructured."""
    print("\n" + "=" * 60)
    print("STEP 3: CLASSIFY")
    print("=" * 60)
    from classify_data import main as classify_main
    classify_main()
    structured = SCRIPT_DIR / 'structured_checklist.json'
    unstructured = SCRIPT_DIR / 'unstructured_checklist.json'
    return structured.exists() and unstructured.exists()


def run_chunk():
    """Step 4: Chunk content into token-limited segments."""
    print("\n" + "=" * 60)
    print("STEP 4: CHUNK")
    print("=" * 60)
    # TODO: Import and run chunker
    print("⚠️  Chunk step not yet implemented")
    print("   Will create: nutrition_chunks.json")
    return True  # Placeholder


def run_embed():
    """Step 5: Generate embeddings for each chunk."""
    print("\n" + "=" * 60)
    print("STEP 5: EMBED")
    print("=" * 60)
    # TODO: Import and run embedder
    print("⚠️  Embed step not yet implemented")
    print("   Will create: nutrition_embedded.json")
    return True  # Placeholder


def run_store():
    """Step 6: Store embeddings in vector database."""
    print("\n" + "=" * 60)
    print("STEP 6: STORE (Vector DB)")
    print("=" * 60)
    # TODO: Import and run vector store loader
    print("⚠️  Store step not yet implemented")
    print("   Will load into: pgvector/Supabase")
    return True  # Placeholder


# Step registry
STEP_FUNCTIONS = {
    'crawl': run_crawl,
    'clean': run_clean,
    'classify': run_classify,
    'chunk': run_chunk,
    'embed': run_embed,
    'store': run_store,
}


def run_pipeline(start_from: str = None, single_step: str = None):
    """
    Run the data pipeline.
    
    Args:
        start_from: Start from this step (skip previous steps)
        single_step: Run only this single step
    """
    print("=" * 60)
    print("NUTRITION ATTRIBUTE DATA PIPELINE")
    print("=" * 60)
    
    if single_step:
        # Run single step
        if single_step not in STEPS:
            print(f"❌ Unknown step: {single_step}")
            print(f"   Valid steps: {', '.join(STEPS)}")
            return False
        
        print(f"Running single step: {single_step}")
        return STEP_FUNCTIONS[single_step]()
    
    # Determine which steps to run
    if start_from:
        if start_from not in STEPS:
            print(f"❌ Unknown step: {start_from}")
            print(f"   Valid steps: {', '.join(STEPS)}")
            return False
        start_idx = STEPS.index(start_from)
    else:
        start_idx = 0
    
    steps_to_run = STEPS[start_idx:]
    print(f"Steps to run: {' → '.join(steps_to_run)}")
    
    # Run each step
    for step in steps_to_run:
        success = STEP_FUNCTIONS[step]()
        if not success:
            print(f"\n❌ Pipeline failed at step: {step}")
            return False
    
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description='Run the nutrition attribute data pipeline')
    parser.add_argument('--from', dest='start_from', 
                        help=f'Start from step: {", ".join(STEPS)}')
    parser.add_argument('--step', dest='single_step',
                        help=f'Run single step: {", ".join(STEPS)}')
    
    args = parser.parse_args()
    
    success = run_pipeline(
        start_from=args.start_from,
        single_step=args.single_step
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
