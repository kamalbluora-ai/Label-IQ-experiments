"""
Nutrition Attribute Data Cleaner
Step 2: Clean raw HTML into structured data.

Based on ARCHITECTURE.md specifications:
- Input: nutrition_raw_crawl.json (raw HTML)
- Output: nutrition_cleaned_data.json
- Extract: headings, tables, clean text
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup, NavigableString

# ============================================================================
# CONFIGURATION
# ============================================================================

# HTML elements to remove entirely
REMOVE_TAGS = [
    'script', 'style', 'noscript', 'iframe', 'svg', 'img', 
    'button', 'input', 'form', 'select', 'textarea'
]

# CSS selectors for navigation/chrome to remove
REMOVE_SELECTORS = [
    'header', 'footer', 'nav',
    '.breadcrumb', '.breadcrumbs', '#breadcrumb',
    '.sidebar', '#sidebar', '.side-nav',
    '.toc', '#toc', '.table-of-contents',
    '.feedback', '#feedback', '.report-problem',
    '.language-toggle', '#language-toggle',
    '.share', '.social-share',
    '.pagination', '.pager',
    '.alert-info', '.alert-warning',  # Often contains "updated on" notices
]

# Patterns indicating "On this page" TOC sections
TOC_PATTERNS = [
    r'on this page',
    r'table of contents',
    r'in this section',
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CleanedPage:
    """Represents a cleaned page."""
    url: str
    title: str
    headings: List[str]
    tables: List[Dict]
    clean_text: str
    char_count: int


# ============================================================================
# CLEANING FUNCTIONS
# ============================================================================

def remove_unwanted_elements(soup: BeautifulSoup) -> None:
    """Remove navigation, scripts, and other unwanted elements."""
    # Remove specific tags
    for tag in REMOVE_TAGS:
        for element in soup.find_all(tag):
            element.decompose()
    
    # Remove by CSS selectors
    for selector in REMOVE_SELECTORS:
        for element in soup.select(selector):
            element.decompose()


def remove_toc_sections(soup: BeautifulSoup) -> None:
    """Remove 'On this page' table of contents sections.
    
    NOTE: Disabled for canada.ca pages - the TOC is useful context
    and the patterns were removing actual content.
    """
    # Disabled - was removing actual content
    pass


def remove_footnotes(soup: BeautifulSoup) -> None:
    """Remove footnote sections."""
    # Common footnote patterns
    footnote_selectors = [
        '.footnotes', '#footnotes',
        '.footnote', '#footnote',
        '[role="doc-endnotes"]',
        '.fn-rtn',  # Footnote return links
    ]
    
    for selector in footnote_selectors:
        for element in soup.select(selector):
            element.decompose()
    
    # Remove sup elements that are footnote references
    for sup in soup.find_all('sup'):
        if sup.find('a'):
            link = sup.find('a')
            href = link.get('href', '')
            if '#fn' in href or '#footnote' in href:
                sup.decompose()


def extract_headings(soup: BeautifulSoup) -> List[str]:
    """Extract all headings with their level."""
    headings = []
    
    for level in range(1, 7):
        for heading in soup.find_all(f'h{level}'):
            text = heading.get_text(strip=True)
            if text and len(text) > 2:  # Skip empty or very short
                headings.append(f"[H{level}] {text}")
    
    return headings


def extract_tables(soup: BeautifulSoup) -> List[Dict]:
    """Extract tables as structured data."""
    tables = []
    
    for table in soup.find_all('table'):
        table_data = {
            "headers": [],
            "rows": []
        }
        
        # Extract headers
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    table_data["headers"].append(th.get_text(strip=True))
        
        # If no thead, try first row
        if not table_data["headers"]:
            first_row = table.find('tr')
            if first_row:
                for cell in first_row.find_all(['th', 'td']):
                    table_data["headers"].append(cell.get_text(strip=True))
        
        # Extract rows
        tbody = table.find('tbody') or table
        for tr in tbody.find_all('tr'):
            # Skip header row if we already got it
            if tr.find('th') and not tr.find('td'):
                continue
            
            row = []
            for cell in tr.find_all(['td', 'th']):
                row.append(cell.get_text(strip=True))
            
            if row:
                table_data["rows"].append(row)
        
        # Only keep tables with actual content
        if table_data["rows"]:
            tables.append(table_data)
    
    return tables


def extract_clean_text(soup: BeautifulSoup, target_sections: List[str] = None) -> str:
    """Extract clean text from main content area or specific sections."""
    
    # If target sections specified, extract only those
    if target_sections:
        section_texts = []
        for section_id in target_sections:
            # Find the section heading element
            section_elem = soup.find(id=section_id)
            if section_elem:
                # Get all content from this section until the next same-level heading
                section_text = []
                
                # Start with the section element itself (usually an h2)
                section_text.append(section_elem.get_text(strip=True))
                
                # Get all following siblings until next h2
                for sibling in section_elem.find_next_siblings():
                    # Stop at next major section (h2 with different ID)
                    if sibling.name == 'h2' and sibling.get('id') and sibling.get('id') != section_id:
                        break
                    section_text.append(sibling.get_text(separator='\n', strip=True))
                
                section_texts.append('\n'.join(section_text))
        
        text = '\n\n'.join(section_texts) if section_texts else ''
    else:
        # Original behavior: get all content
        content = soup.find(class_='mwsgeneric-base-html')
        if not content:
            content = soup.find('main') or soup.find(id='wb-cont') or soup.find(id='main-content')
        if not content:
            content = soup.find('body') or soup
        text = content.get_text(separator='\n', strip=True)
    
    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 newlines
    text = re.sub(r'[ \t]+', ' ', text)  # Collapse horizontal whitespace
    text = '\n'.join(line.strip() for line in text.split('\n'))  # Strip each line
    
    return text.strip()


def clean_page(html: str, url: str, title: str, target_sections: List[str] = None) -> CleanedPage:
    """Clean a single page and extract structured data.
    
    Args:
        html: Raw HTML content
        url: Source URL
        title: Page title
        target_sections: Optional list of section IDs to extract (e.g., ['a3', 'a4'])
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Step 1-4: Remove unwanted elements
    remove_unwanted_elements(soup)
    remove_toc_sections(soup)
    remove_footnotes(soup)
    
    # Step 5: Extract headings (from target sections if specified)
    if target_sections:
        headings = []
        for section_id in target_sections:
            section_elem = soup.find(id=section_id)
            if section_elem:
                # Get headings in this section
                for sibling in [section_elem] + list(section_elem.find_next_siblings()):
                    if sibling.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                        if sibling.name == 'h2' and sibling.get('id') != section_id and sibling.get('id'):
                            break  # Stop at next major section
                        level = sibling.name[1]
                        text = sibling.get_text(strip=True)
                        if text and len(text) > 2:
                            headings.append(f"[H{level}] {text}")
    else:
        headings = extract_headings(soup)
    
    # Step 6: Extract tables (from target sections if specified)
    if target_sections:
        tables = []
        for section_id in target_sections:
            section_elem = soup.find(id=section_id)
            if section_elem:
                for sibling in section_elem.find_next_siblings():
                    if sibling.name == 'h2' and sibling.get('id') != section_id and sibling.get('id'):
                        break
                    for table in sibling.find_all('table') if sibling.name != 'table' else [sibling]:
                        table_data = extract_single_table(table)
                        if table_data:
                            tables.append(table_data)
    else:
        tables = extract_tables(soup)
    
    # Step 7: Extract clean text
    clean_text = extract_clean_text(soup, target_sections)
    
    return CleanedPage(
        url=url,
        title=title,
        headings=headings,
        tables=tables,
        clean_text=clean_text,
        char_count=len(clean_text)
    )


def extract_single_table(table) -> Optional[Dict]:
    """Extract a single table as structured data."""
    table_data = {"headers": [], "rows": []}
    
    thead = table.find('thead')
    if thead:
        header_row = thead.find('tr')
        if header_row:
            for th in header_row.find_all(['th', 'td']):
                table_data["headers"].append(th.get_text(strip=True))
    
    if not table_data["headers"]:
        first_row = table.find('tr')
        if first_row:
            for cell in first_row.find_all(['th', 'td']):
                table_data["headers"].append(cell.get_text(strip=True))
    
    tbody = table.find('tbody') or table
    for tr in tbody.find_all('tr'):
        if tr.find('th') and not tr.find('td'):
            continue
        row = [cell.get_text(strip=True) for cell in tr.find_all(['td', 'th'])]
        if row:
            table_data["rows"].append(row)
    
    return table_data if table_data["rows"] else None


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_cleaner(input_file: str, output_file: str) -> Dict:
    """
    Main cleaning pipeline.
    
    Args:
        input_file: Path to raw crawl JSON
        output_file: Path to save cleaned data
    
    Returns:
        Statistics about the cleaning process
    """
    print("=" * 60)
    print("NUTRITION ATTRIBUTE DATA CLEANER")
    print("=" * 60)
    print(f"\n📂 Input:  {input_file}")
    print(f"   Output: {output_file}")
    
    # Load raw crawl data
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    pages = raw_data.get('pages', [])
    print(f"\n   Found {len(pages)} pages to clean")
    
    # Clean each page
    cleaned_pages = []
    total_tables = 0
    total_headings = 0
    
    for i, page in enumerate(pages):
        if page.get('status') != 'success':
            continue
        
        url = page.get('url', '')
        title = page.get('title', '')
        html = page.get('html', '')
        target_sections = page.get('target_sections', None)
        
        if not html:
            continue
        
        print(f"\n   [{i+1}/{len(pages)}] Cleaning: {url[:60]}...")
        if target_sections:
            print(f"      Target sections: {target_sections}")
        
        cleaned = clean_page(html, url, title, target_sections)
        cleaned_pages.append(asdict(cleaned))
        
        total_tables += len(cleaned.tables)
        total_headings += len(cleaned.headings)
        
        print(f"      Headings: {len(cleaned.headings)}, Tables: {len(cleaned.tables)}, Chars: {cleaned.char_count:,}")
    
    # Save output
    output_data = {
        "source_file": input_file,
        "total_pages": len(cleaned_pages),
        "total_tables": total_tables,
        "total_headings": total_headings,
        "pages": cleaned_pages
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Summary
    print(f"\n" + "=" * 60)
    print("CLEANING COMPLETE")
    print("=" * 60)
    print(f"   Pages cleaned:  {len(cleaned_pages)}")
    print(f"   Total headings: {total_headings}")
    print(f"   Total tables:   {total_tables}")
    print(f"\n✅ Saved to: {output_file}")
    
    return {
        "pages_cleaned": len(cleaned_pages),
        "total_headings": total_headings,
        "total_tables": total_tables
    }


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    input_file = script_dir / "nutrition_raw_crawl.json"
    output_file = script_dir / "nutrition_cleaned_data.json"
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        print("   Run nutrition_attribute_crawl.py first.")
        return
    
    run_cleaner(str(input_file), str(output_file))
    print(f"\nNext step: Run classify.py to split structured vs unstructured")


if __name__ == "__main__":
    main()
