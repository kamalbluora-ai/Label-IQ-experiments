"""
Nutrition Attribute Crawler - URL List Mode
Step 1: Crawl specific URLs provided by user.

Simpler approach: No link following, just fetch the curated list.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import requests
from bs4 import BeautifulSoup

# ============================================================================
# URL LIST - Add more URLs here as needed
# ============================================================================

URLS_TO_CRAWL = [
    "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html#a3",
    "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html#a4",
    "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html#a5",
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CrawledPage:
    """Represents a crawled page."""
    url: str
    title: str
    html: str
    status: str
    target_sections: List[str] = None  # Section IDs to extract (e.g., ['a3', 'a4', 'a5'])
    error_message: Optional[str] = None


# ============================================================================
# CRAWLING
# ============================================================================

def fetch_page(url: str) -> Optional[str]:
    """Fetch HTML content from URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def extract_title(html: str) -> str:
    """Extract page title from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    title_tag = soup.find('title')
    return title_tag.get_text(strip=True) if title_tag else "Untitled"


def crawl_urls(urls: List[str]) -> Dict:
    """Crawl all URLs in the list. Collects target sections from fragments."""
    print("=" * 60)
    print("NUTRITION ATTRIBUTE CRAWLER (URL List Mode)")
    print("=" * 60)
    print(f"\n📋 URLs to crawl: {len(urls)}")
    
    pages = []
    base_url_data = {}  # Track base URLs and their target sections
    
    # First pass: collect all target sections per base URL
    for url in urls:
        base_url = url.split('#')[0]
        fragment = url.split('#')[1] if '#' in url else None
        
        if base_url not in base_url_data:
            base_url_data[base_url] = {'sections': [], 'fetched': False}
        
        if fragment:
            base_url_data[base_url]['sections'].append(fragment)
    
    # Second pass: fetch each unique base URL once
    for i, (base_url, data) in enumerate(base_url_data.items(), 1):
        print(f"\n[{i}/{len(base_url_data)}] {base_url[:60]}...")
        print(f"   Target sections: {data['sections']}")
        
        html = fetch_page(base_url)
        if html:
            title = extract_title(html)
            pages.append(asdict(CrawledPage(
                url=base_url,
                title=title,
                html=html,
                status="success",
                target_sections=data['sections']
            )))
            print(f"   ✅ Success: {title[:50]}...")
        else:
            pages.append(asdict(CrawledPage(
                url=base_url,
                title="",
                html="",
                status="error",
                target_sections=data['sections'],
                error_message="Failed to fetch"
            )))
    
    successful = sum(1 for p in pages if p['status'] == 'success')
    
    print(f"\n" + "=" * 60)
    print("CRAWL COMPLETE")
    print("=" * 60)
    print(f"   Unique pages:   {successful}")
    print(f"   Total sections: {sum(len(d['sections']) for d in base_url_data.values())}")
    
    return {
        "total_urls": len(urls),
        "unique_pages": successful,
        "pages": pages
    }


def save_results(data: Dict, output_file: str):
    """Save crawl results to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved to: {output_file}")


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    output_file = script_dir / "nutrition_raw_crawl.json"
    
    results = crawl_urls(URLS_TO_CRAWL)
    save_results(results, str(output_file))
    
    print(f"\nNext step: Run nutrition_attribute_clean.py")


if __name__ == "__main__":
    main()
