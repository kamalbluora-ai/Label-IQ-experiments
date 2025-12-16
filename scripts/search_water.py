import requests
import sqlite3
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from bs4 import BeautifulSoup
import re, config

def search_for_prepackaged_water():
    """Search specifically for Volume 11 - Prepackaged Water content"""
    
    # URL and client setup
    url = "https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference/canadian-food-compositional-standards-0"
    
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return

    print("Fetching webpage to search for Prepackaged Water content...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        print(f"Error fetching webpage: {e}")
        return
        
    # Clean the content
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    main_content = soup.find('main') or soup.find('div', class_='container') or soup
    clean_text = main_content.get_text(separator='\n', strip=True)
    
    print(f"Searching {len(clean_text)} characters for Prepackaged Water content...")
    
    # Search patterns for prepackaged water
    water_patterns = [
        "prepackaged water",
        "packaged water", 
        "bottled water",
        "volume 11.*water",
        "11\..*water",
        "water.*standard",
        "drinking water",
        "mineral water",
        "spring water"
    ]
    
    found_chunks = []
    
    for pattern in water_patterns:
        print(f"Searching for pattern: '{pattern}'")
        
        # Find all matches
        matches = list(re.finditer(pattern, clean_text, re.IGNORECASE))
        print(f"  Found {len(matches)} matches")
        
        for match in matches[:5]:  # Limit to first 5 matches per pattern
            start_idx = match.start()
            
            # Extract context around the match
            chunk_start = max(0, start_idx - 3000)
            chunk_end = min(len(clean_text), start_idx + 10000)
            chunk = clean_text[chunk_start:chunk_end]
            
            # Show context
            match_text = clean_text[max(0, start_idx - 100):start_idx + 200]
            print(f"    Context: ...{match_text}...")
            
            found_chunks.append({
                'chunk': chunk,
                'pattern': pattern,
                'match_text': match_text
            })
    
    if not found_chunks:
        print("No prepackaged water content found!")
        return
        
    print(f"\nFound {len(found_chunks)} potential water-related chunks")
    
    # Process the most promising chunks
    water_items = []
    
    for i, chunk_info in enumerate(found_chunks[:5]):  # Process top 5 chunks
        chunk = chunk_info['chunk']
        pattern = chunk_info['pattern']
        
        print(f"\nProcessing chunk {i+1} (pattern: {pattern})...")
        
        system_prompt = """You are an expert parser for the Canadian Food Compositional Standards.

Focus specifically on finding common names from Volume 11 – Prepackaged Water.

Extract any water-related common names from the text, especially:
- Prepackaged Water
- Bottled Water  
- Mineral Water
- Spring Water
- Drinking Water
- Any water products with standards

For each water product found, extract:
1. common_name: the water product name
2. definition: the description/standard for that water product  
3. volume: should be "Volume 11 – Prepackaged Water" or similar
4. tag: the section (e.g. "11.1 Prepackaged Water")

Return ONLY pipe-delimited format:
common_name|definition|volume|tag

IMPORTANT: Only extract water-related products. No headers, no extra text."""

        user_prompt = f"""Extract water product common names from this Canadian Food Compositional Standards text.

Focus on Volume 11 - Prepackaged Water content.

{chunk}

Return ONLY pipe-delimited data for water products:
common_name|definition|volume|tag"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=4000
            )

            content = response.choices[0].message.content.strip()
            
            print(f"  Response: {content[:200]}...")
            
            # Parse response
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 4:
                    water_items.append({
                        'common_name': parts[0].strip(),
                        'definition': parts[1].strip(), 
                        'volume': parts[2].strip(),
                        'tag': parts[3].strip()
                    })
                    
        except Exception as e:
            print(f"  Error processing chunk: {e}")
    
    if water_items:
        print(f"\n✅ Found {len(water_items)} water-related common names:")
        for item in water_items:
            print(f"  {item['common_name']} | {item['volume']}")
            
        # Insert into database
        db_file = Path(__file__).parent.parent / "data" / "ilt_requirements.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        inserted = 0
        for item in water_items:
            try:
                cursor.execute("""
                    INSERT INTO cfcs_cname (common_name, definition, volume, tag, source_url, created_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    item['common_name'],
                    item['definition'],
                    item['volume'], 
                    item['tag'],
                    url,
                    datetime.now()
                ))
                inserted += 1
            except Exception as e:
                print(f"Error inserting {item['common_name']}: {e}")
                
        conn.commit()
        conn.close()
        
        print(f"✅ Successfully added {inserted} water-related items to database")
        
    else:
        print("❌ No water-related common names found")

if __name__ == "__main__":
    search_for_prepackaged_water()