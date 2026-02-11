import json, time, os
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

URL = "https://inspection.canada.ca/en/food-labels/labelling/industry"

def norm_text(s):
    return " ".join(s.split()).strip()

def extract_links(element, base_url):
    citations = []
    for link in element.find_all("a"):
        text = norm_text(link.get_text())
        href = link.get("href", "").strip()
        if href and text:
            citations.append({
                "text": text,
                "href": urljoin(base_url, href)
            })
    return citations

def get_next_section_boundary(current_element, section_titles):
    """Find the next element that marks the start of another main section"""
    sibling = current_element.find_next_sibling()
    while sibling:
        if sibling.name in ["h2", "h3"]:
            sibling_text = norm_text(sibling.get_text())
            if sibling_text in section_titles:
                return sibling
        sibling = sibling.find_next_sibling()
    return None

def find_section_content(soup, section_title, all_section_titles):
    section_element = None
    
    for heading in soup.find_all(["h2", "h3"]):
        heading_text = norm_text(heading.get_text())
        if heading_text == section_title:
            section_element = heading
            break
    
    if not section_element:
        return []
    
    # Find where this section ends (next main section starts)
    boundary_element = get_next_section_boundary(section_element, all_section_titles)
    
    citations = []
    current = section_element.find_next_sibling()
    
    while current:
        # Stop if we reached the boundary of the next main section
        if boundary_element and current == boundary_element:
            break
            
        # Stop if we encounter another main section heading
        if current.name in ["h2", "h3"]:
            current_text = norm_text(current.get_text())
            if current_text in all_section_titles and current_text != section_title:
                break
        
        if current.name in ["ul", "ol"]:
            for li in current.find_all("li", recursive=False):
                citations.extend(extract_links(li, URL))
        elif current.name in ["p", "div"]:
            citations.extend(extract_links(current, URL))
        elif current.name in ["h3", "h4", "h5"]:
            # Only process subsection if it's not a main section title
            current_text = norm_text(current.get_text())
            if current_text not in all_section_titles:
                citations.extend(extract_links(current, URL))
        
        current = current.find_next_sibling()
    
    # Remove duplicates
    unique_citations = []
    seen_urls = set()
    for citation in citations:
        if citation["href"] not in seen_urls:
            unique_citations.append(citation)
            seen_urls.add(citation["href"])
    
    return unique_citations

def parse_industry_labelling():
    html = requests.get(URL, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    
    target_sections = [
        "Core labelling requirements",
        "Claims and statements",
        "Food-specific labelling requirements"
    ]
    
    sections = []
    
    for section_title in target_sections:
        citations = find_section_content(soup, section_title, target_sections)
        sections.append({
            "title": section_title,
            "citations": citations
        })
    
    output = {
        "source_url": URL,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sections": sections
    }
    
    return output

if __name__ == "__main__":
    output_dir = "ILT"
    os.makedirs(output_dir, exist_ok=True)
    
    data = parse_industry_labelling()
    output_file = os.path.join(output_dir, "industry_labelling_tool.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    total_citations = sum(len(s["citations"]) for s in data["sections"])
    print(f"Wrote {output_file} with {total_citations} citations across {len(data['sections'])} sections")