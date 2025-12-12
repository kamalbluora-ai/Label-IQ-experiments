import json
import os
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin, urlparse

def normalize_text(element):
    """Extract text with proper spacing between elements"""
    if not element:
        return ""
    
    # Get text with separator to maintain spacing
    text = element.get_text(separator=" ", strip=True)
    # Normalize whitespace - replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def sanitize_folder_name(name):
    """Convert text to valid folder name"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.replace(' ', '_').replace(',', '').replace('-', '_')
    return name.strip('_')
    """Convert text to valid folder name"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.replace(' ', '_').replace(',', '').replace('-', '_')
    return name.strip('_')

def is_external_link(url, base_domain="inspection.canada.ca"):
    """Check if URL is external to the base domain"""
    try:
        parsed = urlparse(url)
        return parsed.netloc and parsed.netloc != base_domain
    except:
        return False

def get_page_content(url):
    """Fetch and parse webpage content"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_sections_and_links(soup, base_url):
    """Extract sections with their content and separate internal/external links"""
    sections = {}
    external_links = []
    
    # Find all h2 elements
    h2_elements = soup.find_all('h2')
    
    for h2 in h2_elements:
        h2_text = normalize_text(h2)
        
        # Skip "On this page", footnote sections, and navigation/menu sections
        skip_sections = [
            'on this page', 'footnote', 'related link', 'language selection', 
            'menu', 'you are here', 'about this site'
        ]
        if any(skip_text in h2_text.lower() for skip_text in skip_sections):
            continue
        
        section_content = {
            'title': h2_text,
            'content': [],
            'internal_links': [],
            'content_with_links': []
        }
        
        # Get content between this h2 and the next h2
        current = h2.find_next_sibling()
        
        while current and current.name != 'h2':
            if current.name in ['p', 'div', 'ul', 'ol', 'li']:
                text_content = normalize_text(current)
                if text_content:
                    # Create content entry with link mapping
                    content_entry = {
                        'text': text_content,
                        'element_type': current.name,
                        'links': []
                    }
                    
                    section_content['content'].append(text_content)
                    
                    # Extract links from this element and map them to content
                    links = current.find_all('a', href=True)
                    for link in links:
                        link_text = normalize_text(link)
                        link_href = link.get('href')
                        
                        if link_text and link_href:
                            # Convert relative URLs to absolute URLs
                            if link_href.startswith('/'):
                                link_href = 'https://inspection.canada.ca' + link_href
                            elif link_href.startswith('#'):
                                link_href = base_url + link_href
                            
                            # Get surrounding context for the link
                            link_context = {
                                'link_text': link_text,
                                'href': link_href,
                                'context_text': text_content,
                                'section': h2_text,
                                'element_type': current.name,
                                'position_in_content': len(section_content['content'])
                            }
                            
                            content_entry['links'].append({
                                'text': link_text,
                                'href': link_href,
                                'is_external': is_external_link(link_href)
                            })
                            
                            link_data = {
                                'text': link_text,
                                'href': link_href,
                                'section': h2_text,
                                'context': text_content,
                                'element_type': current.name
                            }
                            
                            # Separate external and internal links
                            if is_external_link(link_href):
                                external_links.append(link_data)
                            else:
                                section_content['internal_links'].append(link_context)
                    
                    # Add the content entry with its links to content_with_links
                    section_content['content_with_links'].append(content_entry)
            
            current = current.find_next_sibling()
        
        if section_content['content'] or section_content['internal_links']:
            sections[h2_text] = section_content
    
    return sections, external_links

def create_folder_structure_and_parse():
    """Main function to parse JSON and create folder structure"""
    
    # Create base output directory
    base_output_dir = "industry_labelling_tool_parsed"
    os.makedirs(base_output_dir, exist_ok=True)
    
    # Read the JSON file
    json_file_path = "ILT/industry_labelling_tool.json"
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_file_path} not found!")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return
    
    # Process each main section
    for section in data['sections']:
        section_title = section['title']
        section_folder = sanitize_folder_name(section_title)
        section_path = os.path.join(base_output_dir, section_folder)
        os.makedirs(section_path, exist_ok=True)
        
        print(f"Processing section: {section_title}")
        
        # Process each citation in the section
        for citation in section['citations']:
            citation_text = citation['text']
            citation_href = citation['href']
            
            # Create folder for each citation
            citation_folder = sanitize_folder_name(citation_text)
            citation_path = os.path.join(section_path, citation_folder)
            os.makedirs(citation_path, exist_ok=True)
            
            print(f"Processing citation: {citation_text}")
            print(f"URL: {citation_href}")

            # Fetch and parse the webpage
            soup = get_page_content(citation_href)
            if soup:
                # Extract sections and content with separated links
                page_sections, external_links = extract_sections_and_links(soup, citation_href)
                
                if page_sections:
                    # Save main content to content.json
                    content_data = {
                        'source_url': citation_href,
                        'citation_title': citation_text,
                        'sections': page_sections
                    }
                    
                    content_file_path = os.path.join(citation_path, 'content.json')
                    with open(content_file_path, 'w', encoding='utf-8') as f:
                        json.dump(content_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"Content saved to: content.json")
                    print(f"Found {len(page_sections)} sections")
                    
                    # Save external links to external_links.json if any exist
                    if external_links:
                        external_links_data = {
                            'source_url': citation_href,
                            'citation_title': citation_text,
                            'external_links': external_links
                        }
                        
                        external_links_file_path = os.path.join(citation_path, 'external_links.json')
                        with open(external_links_file_path, 'w', encoding='utf-8') as f:
                            json.dump(external_links_data, f, indent=2, ensure_ascii=False)
                        
                        print(f"External links saved to: external_links.json")
                        print(f"Found {len(external_links)} external links")
                    else:
                        print(f"No external links found")
                else:
                    print(f"No content sections found")
            else:
                print(f"Failed to fetch content")
            
            # Add delay to be respectful to the server
            time.sleep(1)
    
    print(f"\nProcessing complete! Output saved to: {base_output_dir}")

if __name__ == "__main__":
    create_folder_structure_and_parse()