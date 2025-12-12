
import requests
from bs4 import BeautifulSoup
import json
import os

# URLs to scrape
URLS = {
    "country_of_origin": "https://inspection.canada.ca/en/food-labels/labelling/industry/country-origin",
    "dealer_identity": "https://inspection.canada.ca/en/food-labels/labelling/industry/name-and-principal-place-business"
}

OUTPUT_FILE = "coo_rules.json"

def scrape_cfia_page(url):
    """Scrapes a CFIA page for rules and information, returning only title and content."""
    print(f"Scraping {url}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        main_content = soup.find('main') or soup.find('div', {'role': 'main'}) or soup.find('body')
        
        if not main_content:
            return []

        content_structure = []
        current_section = {"title": "Introduction", "content": []}
        
        for element in main_content.find_all(['h2', 'h3', 'p', 'ul', 'ol']):
            if element.name in ['h2', 'h3']:
                # Save previous section if it has content
                if current_section["content"]:
                    content_structure.append(current_section)
                
                # Start new section
                current_section = {
                    "title": element.get_text(strip=True),
                    "content": []
                }
            elif element.name == 'p':
                text = element.get_text(strip=True)
                if text:
                    current_section["content"].append(text)
            elif element.name in ['ul', 'ol']:
                # Flatten list items into the content list
                items = [li.get_text(strip=True) for li in element.find_all('li')]
                if items:
                    current_section["content"].extend(items)
        
        # Append the last section
        if current_section["content"]:
            content_structure.append(current_section)
            
        return content_structure

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def main():
    # Simple structure: top level keys for each URL, containing list of sections
    data = {}
    
    for key, url in URLS.items():
        data[key] = scrape_cfia_page(url)
        
    # Save to JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully scraped rules to {os.path.abspath(OUTPUT_FILE)}")

if __name__ == "__main__":
    main()
