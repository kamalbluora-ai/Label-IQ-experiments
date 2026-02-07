"""
CFIA Checklist Crawler

Crawls the CFIA requirements checklist page and saves the content as markdown.
This is step 1 of Pipeline 1: Question Extraction.

Usage:
    python cfia_crawler.py

Output:
    - cfia_checklist.md: Raw markdown content from the CFIA checklist page
"""

import asyncio
from pathlib import Path
from datetime import datetime
from crawl4ai import AsyncWebCrawler

# CFIA Requirements Checklist URL
CFIA_CHECKLIST_URL = "https://inspection.canada.ca/en/food-labels/labelling/industry/requirements-checklist"

# Output file
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "cfia_checklist.md"


async def crawl_cfia_checklist() -> str:
    """
    Crawl the CFIA checklist page and return markdown content.
    """
    print(f"Crawling: {CFIA_CHECKLIST_URL}")
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=CFIA_CHECKLIST_URL)
        
        if not result.success:
            raise Exception(f"Failed to crawl: {result.error_message}")
        
        return result.markdown


def save_markdown(content: str, output_path: Path) -> None:
    """
    Save markdown content with metadata header.
    """
    header = f"""---
source_url: {CFIA_CHECKLIST_URL}
crawled_at: {datetime.now().isoformat()}
---

"""
    
    full_content = header + content
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    print(f"Saved to: {output_path}")
    print(f"Content length: {len(content)} characters")


async def main():
    """
    Main function: Crawl CFIA checklist and save as markdown.
    """
    print("=" * 60)
    print("CFIA Checklist Crawler")
    print("=" * 60)
    
    # Crawl
    markdown_content = await crawl_cfia_checklist()
    
    # Save
    save_markdown(markdown_content, OUTPUT_FILE)
    
    print("=" * 60)
    print("Done! Next step: Run question_extractor.py")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())