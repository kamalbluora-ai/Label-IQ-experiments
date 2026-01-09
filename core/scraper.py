"""
Web Scraper for CFIA Food Labelling Requirements Checklist.

This module scrapes the raw content from the CFIA requirements checklist page
and extracts specific sections for further processing.

Source: https://inspection.canada.ca/en/food-labels/labelling/industry/requirements-checklist
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import re


# CFIA Requirements Checklist URL
CFIA_REQUIREMENTS_CHECKLIST_URL = "https://inspection.canada.ca/en/food-labels/labelling/industry/requirements-checklist"


def fetch_page(url: str = CFIA_REQUIREMENTS_CHECKLIST_URL) -> str:
    """
    Fetch the HTML content from the given URL.
    
    Args:
        url: URL to fetch
    
    Returns:
        Raw HTML content as string
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def extract_section_text(html: str, section_name: str, next_section_name: Optional[str] = None) -> str:
    """
    Extract the raw text content of a specific section from the HTML.
    
    Args:
        html: Raw HTML content
        section_name: Name of the section header to extract (e.g., "Common name")
        next_section_name: Name of the next section header to stop at
    
    Returns:
        Raw text content of the section including all bullet points
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all headers (h2, h3, h4)
    headers = soup.find_all(['h2', 'h3', 'h4'])
    
    section_start = None
    section_end = None
    
    # Find the section start
    for i, header in enumerate(headers):
        header_text = header.get_text(strip=True).lower()
        if section_name.lower() in header_text:
            section_start = header
            # Find the next section
            if next_section_name:
                for j in range(i + 1, len(headers)):
                    next_header_text = headers[j].get_text(strip=True).lower()
                    if next_section_name.lower() in next_header_text:
                        section_end = headers[j]
                        break
            else:
                # Just get the next header of same or higher level
                for j in range(i + 1, len(headers)):
                    if headers[j].name <= header.name:
                        section_end = headers[j]
                        break
            break
    
    if not section_start:
        return f"Section '{section_name}' not found in the page."
    
    # Extract all content between section_start and section_end
    content_parts = []
    current = section_start.find_next_sibling()
    
    while current:
        # Stop if we hit the next section
        if section_end and current == section_end:
            break
        # Also stop if we hit a header that might be section_end
        if current.name in ['h2', 'h3'] and section_end is None:
            if current != section_start:
                break
        
        # Extract text from this element
        if current.name == 'ul':
            # Handle lists - preserve bullet structure
            for li in current.find_all('li', recursive=False):
                # Get only DIRECT text, not nested ul content
                direct_text_parts = []
                for child in li.children:
                    if isinstance(child, str):
                        text = child.strip()
                        if text:
                            direct_text_parts.append(text)
                    elif child.name and child.name != 'ul':
                        # Include text from inline elements like <a>, <strong>, etc.
                        text = child.get_text(strip=True)
                        if text:
                            direct_text_parts.append(text)
                
                bullet_text = ' '.join(direct_text_parts)
                if bullet_text:
                    content_parts.append(f"• {bullet_text}")
                
                # Check for nested lists
                nested_ul = li.find('ul')
                if nested_ul:
                    for nested_li in nested_ul.find_all('li', recursive=False):
                        nested_text = nested_li.get_text(separator=' ', strip=True)
                        content_parts.append(f"  ◦ {nested_text}")
        elif current.name == 'p':
            text = current.get_text(strip=True)
            if text:
                content_parts.append(text)
        elif current.name == 'div':
            # Recursively get text from divs
            text = current.get_text(separator='\n', strip=True)
            if text:
                content_parts.append(text)
        
        current = current.find_next_sibling()
    
    return '\n'.join(content_parts)


def scrape_requirements_checklist() -> Dict[str, str]:
    """
    Scrape all sections from the CFIA requirements checklist.
    
    Returns:
        Dictionary with section names as keys and raw text as values
    """
    html = fetch_page()
    
    # Define sections and their next sections
    sections = [
        ("Common name", "Net quantity declaration"),
        ("Net quantity declaration", "List of ingredients and allergen labelling"),
        ("List of ingredients and allergen labelling", "Name and principal place of business"),
        ("Name and principal place of business", "Date markings"),
        ("Date markings", "Nutrition labelling"),
        ("Nutrition labelling", "Front-of-package"),
        ("Front-of-package", "Bilingual requirements"),
        ("Bilingual requirements", "Irradiation"),
        ("Irradiation", "Sweeteners"),
        ("Sweeteners", "Country of origin"),
        ("Country of origin", None),
    ]
    
    results = {}
    for section_name, next_section in sections:
        try:
            content = extract_section_text(html, section_name, next_section)
            results[section_name] = content
        except Exception as e:
            results[section_name] = f"Error extracting section: {str(e)}"
    
    return results


def scrape_section(section_name: str, next_section_name: Optional[str] = None) -> str:
    """
    Scrape a specific section from the CFIA requirements checklist.
    
    Args:
        section_name: Name of the section to scrape
        next_section_name: Name of the next section (to know where to stop)
    
    Returns:
        Raw text content of the section
    """
    html = fetch_page()
    return extract_section_text(html, section_name, next_section_name)


if __name__ == "__main__":
    # Demo: scrape Common Name section
    print("=" * 60)
    print("Scraping CFIA Requirements Checklist - Common Name Section")
    print("=" * 60)
    
    content = scrape_section("Common name", "Net quantity declaration")
    print(content)
    
    print("\n" + "=" * 60)
    print("Scraping CFIA Requirements Checklist - Net Quantity Section")
    print("=" * 60)
    
    content = scrape_section("Net quantity declaration", "List of ingredients")
    print(content)
