import requests
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from bs4 import BeautifulSoup
import re, config

def create_cfcs_cname_table():
    """Create and populate cfcs_cname table from CFCS common names webpage using OpenAI GPT"""
    
    # URL to scrape
    url = "https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference/canadian-food-compositional-standards-0"
    db_file = Path("ilt_requirements.db")
    
    # OpenAI Client - Replace with your API key
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)  # Replace with your actual API key
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        print("Please set your OpenAI API key in the script or environment variable")
        return
    
    # Connect to SQLite database
    if not db_file.exists():
        print(f"Error: Database {db_file} does not exist!")
        print("Please run create_ilt_database.py first.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"Creating cfcs_cname table in: {db_file}")
    
    # Drop existing table to avoid schema conflicts
    cursor.execute("DROP TABLE IF EXISTS cfcs_cname")
    print("Dropped existing cfcs_cname table (if it existed)")
    
    # Create cfcs_cname table with updated schema
    create_table_sql = """
    CREATE TABLE cfcs_cname (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        common_name TEXT NOT NULL,
        definition TEXT,
        volume TEXT,
        tag TEXT,
        source_url TEXT,
        created_date DATETIME NOT NULL
    )
    """
    
    cursor.execute(create_table_sql)
    print("Table 'cfcs_cname' created with new schema")
    
    # Reset sequence (not needed since table was dropped, but good practice)
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='cfcs_cname'")
    conn.commit()
    print("Database changes committed")
    
    # Fetch the webpage
    print(f"Fetching webpage: {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html_content = response.text
    except requests.RequestException as e:
        print(f"Error fetching webpage: {e}")
        conn.close()
        return
    
    print("Webpage fetched successfully")
    
    # Extract common names using OpenAI GPT
    print("Extracting common names using OpenAI GPT...")
    try:
        extracted_data = extract_cnames_with_gpt(client, html_content)
        print(f"Extracted {len(extracted_data)} common names")
        
        if not extracted_data:
            print("No data extracted. Check GPT response and API key.")
            conn.close()
            return
            
    except Exception as e:
        print(f"Error extracting data with GPT: {e}")
        conn.close()
        return
    
    # Insert results into database
    records_inserted = 0
    created_date = datetime.now()
    
    for item in extracted_data:
        try:
            insert_sql = """
            INSERT INTO cfcs_cname (common_name, definition, volume, tag, source_url, created_date) 
            VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_sql, (
                item.get("common_name", ""),
                item.get("definition", ""),
                item.get("volume", ""),
                item.get("tag", ""),
                url,
                created_date
            ))
            records_inserted += 1
            
            # Show progress every 100 records
            if records_inserted % 100 == 0:
                print(f"  Inserted {records_inserted} records...")
                
        except Exception as e:
            print(f"Error inserting record: {e}")
            continue
    
    # Commit changes
    conn.commit()
    
    print(f"\nTotal records inserted: {records_inserted}")
    
    # Display summary
    print(f"\n{'='*60}")
    print("CFCS COMMON NAMES TABLE SUMMARY")
    print(f"{'='*60}")
    
    cursor.execute("SELECT COUNT(*) FROM cfcs_cname")
    total_records = cursor.fetchone()[0]
    print(f"Total records in cfcs_cname: {total_records}")
    
    # Summary by volume
    cursor.execute("""
    SELECT volume, COUNT(*) as name_count
    FROM cfcs_cname 
    WHERE volume IS NOT NULL AND volume != ''
    GROUP BY volume 
    ORDER BY name_count DESC
    """)
    
    print(f"\nCOMMON NAMES BY VOLUME:")
    for volume, name_count in cursor.fetchall():
        print(f"  {volume}: {name_count} names")
    
    # Summary by tag
    cursor.execute("""
    SELECT tag, COUNT(*) as name_count
    FROM cfcs_cname 
    WHERE tag IS NOT NULL AND tag != ''
    GROUP BY tag 
    ORDER BY name_count DESC
    LIMIT 10
    """)
    
    print(f"\nTOP 10 TAGS:")
    for tag, name_count in cursor.fetchall():
        print(f"  {tag}: {name_count} names")
    
    # Show sample records
    print(f"\n{'='*60}")
    print("SAMPLE COMMON NAMES")
    print(f"{'='*60}")
    
    cursor.execute("""
    SELECT id, common_name, volume, tag,
           SUBSTR(definition, 1, 60) as definition_preview
    FROM cfcs_cname 
    ORDER BY id
    LIMIT 15
    """)
    
    sample_records = cursor.fetchall()
    for record in sample_records:
        print(f"ID: {record[0]}")
        print(f"Common Name: {record[1]}")
        print(f"Volume: {record[2]}")
        print(f"Tag: {record[3]}")
        print(f"Definition Preview: {record[4]}...")
        print("-" * 40)
    
    conn.close()
    print(f"\nCFCS common names table updated successfully!")
    
    # Final validation: Check for missing volumes and fetch them
    print(f"\n{'='*60}")
    print("VOLUME VALIDATION AND GAP FILLING")
    print(f"{'='*60}")
    
    validate_and_fill_missing_volumes(url, db_file, client)

def extract_cnames_with_gpt(client, html_content):
    """Extract common names from HTML using OpenAI GPT with chunking"""
    
    # First, extract and clean the main content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, style, and other non-content elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    # Find main content
    main_content = soup.find('main') or soup.find('div', class_='container') or soup
    
    # Extract clean text content
    clean_text = main_content.get_text(separator='\n', strip=True)
    
    print(f"Total content length: {len(clean_text)} characters")
    
    # Improved chunking strategy with adaptive sizing
    max_chunk_size = 15000  # Start with this size
    overlap_size = 3000     # Overlap to avoid cutting in middle of definitions
    chunks = []
    truncation_count = 0    # Track truncated responses to adjust chunk size
    
    def create_chunks(text, chunk_size):
        """Create chunks with the specified size"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If this isn't the last chunk, try to find a good break point
            if end < len(text):
                # Look for good break points within the overlap zone
                search_start = max(start + chunk_size - overlap_size, start)
                
                # Try multiple break points
                break_patterns = [
                    r'\nVolume \d+',           # Volume headers
                    r'\n\d+\.\d+\.\d+',       # Section numbers (e.g., 6.1.15)  
                    r'\n\d+\.\d+',            # Section numbers (e.g., 6.1)
                    r'\n[A-Z][a-z]+ [A-Z]',   # Food names starting sentences
                    r'\n\s*\n',               # Double newlines
                ]
                
                best_break = end
                for pattern in break_patterns:
                    matches = list(re.finditer(pattern, text[search_start:end + overlap_size]))
                    if matches:
                        # Use the last match to get a good break point
                        last_match = matches[-1]
                        potential_break = search_start + last_match.start()
                        if potential_break > start + chunk_size // 2:  # Don't break too early
                            best_break = potential_break
                            break
                
                end = min(best_break, len(text))
            
            chunk = text[start:end].strip()
            if chunk and len(chunk) > 100:  # Only include substantial chunks
                chunks.append(chunk)
            
            start = end
            
            # Prevent infinite loop
            if start >= len(text):
                break
                
        return chunks
    
    # Initial chunking
    chunks = create_chunks(clean_text, max_chunk_size)
    
    print(f"Initial chunking: Split content into {len(chunks)} chunks with max size {max_chunk_size}")
    for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
        print(f"  Chunk {i+1}: {len(chunk)} chars, starts with: {chunk[:60]}...")
    
    # Process each chunk
    all_extracted_data = []
    
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
        
        system_prompt = """You are an expert parser for the Canadian Food Compositional Standards.

Extract common names from the text. A common name is a food name that appears in bold formatting in the original document.

IMPORTANT RULES:
1. Extract COMPLETE food names including all variations and alternatives
2. For compound names like "Cardamom or Cardamom Seed" - extract as TWO separate entries
3. For names with alternatives like "Wine Vinegar or Red Wine Vinegar" - extract BOTH names
4. For template names like "Canned (naming the poultry)" - extract as "Canned Poultry"
5. Clean section numbers but keep the full food name

Look for patterns like:
- "6.1.15 Cardamom or Cardamom Seed" → Extract both "Cardamom" AND "Cardamom Seed"
- "15.1.12 Glucose or Glucose Syrup" → Extract both "Glucose" AND "Glucose Syrup"  
- "16.1.2 Spirit Vinegar, Alcohol Vinegar, White Vinegar or Grain Vinegar" → Extract ALL 4 names

For each food name found, extract these 4 fields:
1. common_name: the actual food name (complete name, no section numbers)
2. definition: the description that follows the name (first sentence is enough)
3. volume: the Volume heading (e.g. "Volume 6 – Spices, Seasonings and Dressings for Salads")
4. tag: the section heading (e.g. "6.1 Spices and Seasonings")

Return ONLY a pipe-delimited format with one food per line:
common_name|definition|volume|tag

Example:
Cardamom|is the dried seed of Elettaria cardamomum|Volume 6 – Spices, Seasonings and Dressings for Salads|6.1 Spices and Seasonings
Cardamom Seed|is the dried seed of Elettaria cardamomum|Volume 6 – Spices, Seasonings and Dressings for Salads|6.1 Spices and Seasonings

IMPORTANT: If you approach token limits, prioritize completing full entries rather than starting incomplete ones.
Only include actual food names, not section numbers, navigation text, or French translations. No headers, no extra text."""

        user_prompt = f"""Extract all food common names from this Canadian Food Compositional Standards text chunk.

REMEMBER: Extract EACH alternative name as a separate entry (e.g., "Cardamom or Cardamom Seed" = 2 entries)

{chunk}

Return ONLY pipe-delimited data, one food per line, no headers:
common_name|definition|volume|tag"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=16000  # Maximum allowed for gpt-4o-mini
            )

            # Get the response content
            content = response.choices[0].message.content.strip()
            
            # Check if response was truncated
            finish_reason = response.choices[0].finish_reason
            was_truncated = finish_reason == "length"
            
            if was_truncated:
                print(f"  WARNING: Response was truncated due to token limit!")
                print(f"  Raw response preview: {content[:100]}...")
                print(f"  Response ends with: ...{content[-50:]}")
                
                # Track truncations for adaptive chunking
                truncation_count += 1
                
                # If we're getting too many truncations, re-chunk with smaller size
                if truncation_count >= 3 and max_chunk_size > 8000:
                    print(f"  Too many truncations ({truncation_count}), reducing chunk size...")
                    max_chunk_size = max_chunk_size // 2
                    print(f"  New chunk size: {max_chunk_size}")
                    
                    # Re-chunk remaining chunks with smaller size
                    remaining_chunks = chunks[i+1:]
                    if remaining_chunks:
                        # Combine remaining text and re-chunk
                        remaining_text = '\n'.join(remaining_chunks)
                        new_chunks = create_chunks(remaining_text, max_chunk_size)
                        chunks = chunks[:i+1] + new_chunks
                        print(f"  Re-chunked remaining content into {len(new_chunks)} smaller chunks")
                        
            else:
                print(f"  Raw response preview: {content[:100]}...")
            
            # Parse pipe-delimited format into JSON objects
            parsed_data = []
            
            try:
                lines = content.strip().split('\n')
                valid_line_count = 0
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line or line.startswith('#') or '|' not in line:
                        continue  # Skip empty lines, comments, or invalid lines
                    
                    parts = line.split('|')
                    if len(parts) >= 4:
                        # Extract the 4 required fields
                        common_name = parts[0].strip()
                        definition = parts[1].strip()
                        volume = parts[2].strip()
                        tag = parts[3].strip()
                        
                        # Basic validation
                        if common_name and len(common_name) > 2:
                            item = {
                                "common_name": common_name,
                                "definition": definition,
                                "volume": volume,
                                "tag": tag
                            }
                            parsed_data.append(item)
                            valid_line_count += 1
                    else:
                        # If this is the last line and response was truncated, this is expected
                        if was_truncated and line_num == len(lines):
                            print(f"  Skipping incomplete last line due to truncation: {line[:50]}...")
                        else:
                            print(f"  Skipping malformed line {line_num}: {line[:50]}...")
                
                print(f"  Successfully parsed {len(parsed_data)} items from pipe-delimited format")
                
                if was_truncated and valid_line_count > 0:
                    print(f"  Note: Extracted {valid_line_count} complete entries despite truncation")
                
            except Exception as parse_error:
                print(f"  Error parsing pipe-delimited format: {parse_error}")
                print(f"  Content preview: {content[:200]}...")
                continue
            
            # Use the parsed data directly since we already validated it during parsing
            valid_items = parsed_data
            
            print(f"  Extracted {len(valid_items)} valid items from chunk {i+1}")
            
            # Show sample of what was extracted from this chunk
            if valid_items:
                sample_names = [item["common_name"] for item in valid_items[:3]]
                print(f"  Sample names: {sample_names}")
            
            all_extracted_data.extend(valid_items)
            
        except Exception as e:
            print(f"  Error processing chunk {i+1}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"Total extracted items from all chunks: {len(all_extracted_data)}")
    
    # Remove duplicates based on common_name (case-insensitive)
    seen_names = set()
    unique_data = []
    
    for item in all_extracted_data:
        name_lower = item["common_name"].lower()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique_data.append(item)
    
    print(f"After removing duplicates: {len(unique_data)} unique items")
    
    return unique_data

def validate_and_fill_missing_volumes(url, db_file, client):
    """Validate volume coverage and fetch missing volumes' content"""
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Get currently extracted volumes
    cursor.execute("SELECT DISTINCT volume FROM cfcs_cname WHERE volume IS NOT NULL AND volume != '' ORDER BY volume")
    current_volumes = [row[0] for row in cursor.fetchall()]
    
    print(f"Currently extracted volumes ({len(current_volumes)}):")
    for vol in current_volumes:
        cursor.execute("SELECT COUNT(*) FROM cfcs_cname WHERE volume = ?", (vol,))
        count = cursor.fetchone()[0]
        print(f"  {vol}: {count} common names")
    
    # Define expected volumes based on CFCS standards
    expected_volumes = [
        "Volume 1 – General",
        "Volume 2 – Alcoholic Beverages", 
        "Volume 3 – Baking Powder",
        "Volume 4 – Cocoa and Chocolate Products",
        "Volume 5 – Coffee",
        "Volume 6 – Spices, Seasonings and Dressings for Salads",
        "Volume 7 – Dairy Products",
        "Volume 8 – Fats and Oils", 
        "Volume 9 – Flavouring Preparations",
        "Volume 10 – Fruits, Vegetables, Their Products and Substitutes",
        "Volume 11 – Gelatin",
        "Volume 11 – Prepackaged Water",  # Additional Volume 11
        "Volume 12 – Grain and Bakery Products",
        "Volume 13 – Meat, Its Preparations and Products",
        "Volume 14 – Salt Standard",
        "Volume 15 – Sweetening Agents Standards",
        "Volume 16 – Vinegar Standards", 
        "Volume 17 – Tea",
        "Volume 18 – Marine and Fresh Water Animal Products",
        "Volume 19 – Poultry Products",
        "Volume 20 – Egg Products"
    ]
    
    # Identify missing volumes using fuzzy matching
    missing_volumes = []
    for expected in expected_volumes:
        # Check if any current volume contains key parts of the expected volume
        found = False
        expected_key_parts = expected.split('–')[1].strip() if '–' in expected else expected
        
        for current in current_volumes:
            current_key_parts = current.split('–')[1].strip() if '–' in current else current
            if expected_key_parts.lower() in current_key_parts.lower() or current_key_parts.lower() in expected_key_parts.lower():
                found = True
                break
                
        if not found:
            missing_volumes.append(expected)
    
    if missing_volumes:
        print(f"\nMissing volumes ({len(missing_volumes)}):")
        for vol in missing_volumes:
            print(f"  {vol}")
        
        # Fetch additional content for missing volumes
        print(f"\nAttempting to fetch content for missing volumes...")
        
        try:
            # Re-fetch the webpage to look for missing content
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            
            # Extract content specifically targeting missing volumes
            additional_data = extract_missing_volume_content(client, html_content, missing_volumes)
            
            if additional_data:
                print(f"Found {len(additional_data)} additional common names from missing volumes")
                
                # Insert additional data
                records_inserted = 0
                created_date = datetime.now()
                
                for item in additional_data:
                    try:
                        insert_sql = """
                        INSERT INTO cfcs_cname (common_name, definition, volume, tag, source_url, created_date) 
                        VALUES (?, ?, ?, ?, ?, ?)
                        """
                        cursor.execute(insert_sql, (
                            item.get("common_name", ""),
                            item.get("definition", ""),
                            item.get("volume", ""),
                            item.get("tag", ""),
                            url,
                            created_date
                        ))
                        records_inserted += 1
                        
                    except Exception as e:
                        print(f"Error inserting additional record: {e}")
                        continue
                
                conn.commit()
                print(f"Added {records_inserted} additional common names")
                
                # Show updated summary
                cursor.execute("SELECT COUNT(*) FROM cfcs_cname")
                total_records = cursor.fetchone()[0]
                print(f"Total records in database: {total_records}")
                
            else:
                print("No additional content found for missing volumes")
                
        except Exception as e:
            print(f"Error fetching additional content: {e}")
    else:
        print(f"\n✅ All expected volumes appear to be covered!")
        
    # Final volume coverage summary
    cursor.execute("SELECT DISTINCT volume FROM cfcs_cname WHERE volume IS NOT NULL AND volume != '' ORDER BY volume")
    final_volumes = cursor.fetchall()
    
    print(f"\nFinal volume coverage: {len(final_volumes)} volumes")
    for vol_row in final_volumes:
        vol = vol_row[0]
        cursor.execute("SELECT COUNT(*) FROM cfcs_cname WHERE volume = ?", (vol,))
        count = cursor.fetchone()[0]
        print(f"  {vol}: {count} names")
    
    conn.close()

def extract_missing_volume_content(client, html_content, missing_volumes):
    """Extract content specifically for missing volumes using targeted search"""
    
    from bs4 import BeautifulSoup
    
    # Clean the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    main_content = soup.find('main') or soup.find('div', class_='container') or soup
    clean_text = main_content.get_text(separator='\n', strip=True)
    
    print(f"Searching {len(clean_text)} characters for missing volume content...")
    
    # Create targeted chunks that might contain missing volume content
    targeted_chunks = []
    
    for missing_vol in missing_volumes:
        # Extract volume number and name
        vol_parts = missing_vol.split('–')
        if len(vol_parts) >= 2:
            vol_num = vol_parts[0].strip()  # e.g., "Volume 11"
            vol_topic = vol_parts[1].strip()  # e.g., "Gelatin"
            
            # Search for content related to this volume
            vol_patterns = [
                vol_num,  # "Volume 11" 
                vol_topic,  # "Gelatin"
                vol_topic.split()[0] if vol_topic else "",  # First word like "Marine"
            ]
            
            for pattern in vol_patterns:
                if not pattern or len(pattern) < 4:
                    continue
                    
                # Find all occurrences of this pattern
                start_idx = 0
                while True:
                    idx = clean_text.lower().find(pattern.lower(), start_idx)
                    if idx == -1:
                        break
                    
                    # Extract a chunk around this occurrence
                    chunk_start = max(0, idx - 5000)  # 5k chars before
                    chunk_end = min(len(clean_text), idx + 15000)  # 15k chars after
                    chunk = clean_text[chunk_start:chunk_end]
                    
                    if len(chunk) > 1000:  # Only include substantial chunks
                        targeted_chunks.append({
                            'content': chunk,
                            'target_volume': missing_vol,
                            'pattern': pattern
                        })
                    
                    start_idx = idx + 1000  # Move forward to avoid duplicates
    
    # Remove duplicate chunks
    unique_chunks = []
    seen_content = set()
    
    for chunk_info in targeted_chunks:
        chunk_hash = hash(chunk_info['content'][:1000])  # Hash first 1k chars
        if chunk_hash not in seen_content:
            seen_content.add(chunk_hash)
            unique_chunks.append(chunk_info)
    
    print(f"Created {len(unique_chunks)} targeted chunks for missing volumes")
    
    # Process targeted chunks
    all_extracted_data = []
    
    for i, chunk_info in enumerate(unique_chunks[:10]):  # Limit to 10 chunks to avoid token overuse
        chunk = chunk_info['content']
        target_vol = chunk_info['target_volume']
        pattern = chunk_info['pattern']
        
        print(f"Processing targeted chunk {i+1}/{min(len(unique_chunks), 10)} for {target_vol} (pattern: {pattern})...")
        
        system_prompt = f"""You are an expert parser for the Canadian Food Compositional Standards.

Focus specifically on finding common names from {target_vol}.

Extract common names from the text. Look for food names that would belong to {target_vol}.

For each food name found, extract these 4 fields:
1. common_name: the actual food name (complete name, no section numbers)
2. definition: the description that follows the name (first sentence is enough)
3. volume: the Volume heading (should be {target_vol} or similar)
4. tag: the section heading (e.g. "11.1 Gelatin")

Return ONLY a pipe-delimited format with one food per line:
common_name|definition|volume|tag

IMPORTANT: Only extract names that clearly belong to {target_vol}. If you approach token limits, prioritize completing full entries.
No headers, no extra text."""

        user_prompt = f"""Extract food common names specifically related to {target_vol} from this text chunk.

Target volume: {target_vol}
Search pattern: {pattern}

{chunk}

Return ONLY pipe-delimited data for foods from {target_vol}:
common_name|definition|volume|tag"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=8000  # Smaller tokens for targeted extraction
            )

            content = response.choices[0].message.content.strip()
            finish_reason = response.choices[0].finish_reason
            
            if finish_reason == "length":
                print(f"  WARNING: Response truncated for {target_vol}")
            
            # Parse the response
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 4:
                    common_name = parts[0].strip()
                    definition = parts[1].strip()
                    volume = parts[2].strip()
                    tag = parts[3].strip()
                    
                    if common_name and len(common_name) > 2:
                        item = {
                            "common_name": common_name,
                            "definition": definition,
                            "volume": volume,
                            "tag": tag
                        }
                        all_extracted_data.append(item)
                        
            print(f"  Extracted {len([line for line in content.split('\n') if '|' in line])} items for {target_vol}")
            
        except Exception as e:
            print(f"  Error processing chunk for {target_vol}: {e}")
            continue
    
    # Remove duplicates
    seen_names = set()
    unique_data = []
    
    for item in all_extracted_data:
        name_lower = item["common_name"].lower()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique_data.append(item)
    
    print(f"Extracted {len(unique_data)} unique items from missing volume search")
    
    return unique_data

def view_cfcs_cname_stats():
    """Optional: View statistics about the cfcs_cname table"""
    db_file = Path("ilt_requirements.db")
    
    if not db_file.exists():
        print("Database not found.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cfcs_cname'")
    if not cursor.fetchone():
        print("Table 'cfcs_cname' does not exist.")
        conn.close()
        return
    
    # Content statistics
    print("\nCFCS COMMON NAMES STATISTICS:")
    
    cursor.execute("""
    SELECT 
        COUNT(*) as total_names,
        COUNT(CASE WHEN definition IS NOT NULL AND definition != '' THEN 1 END) as names_with_def,
        COUNT(CASE WHEN volume IS NOT NULL AND volume != '' THEN 1 END) as names_with_volume,
        COUNT(CASE WHEN tag IS NOT NULL AND tag != '' THEN 1 END) as names_with_tag,
        AVG(LENGTH(common_name)) as avg_name_length,
        AVG(LENGTH(definition)) as avg_def_length
    FROM cfcs_cname
    """)
    
    stats = cursor.fetchone()
    print(f"  Total common names: {stats[0]}")
    print(f"  Names with definitions: {stats[1]}")
    print(f"  Names with volumes: {stats[2]}")
    print(f"  Names with tags: {stats[3]}")
    print(f"  Average name length: {stats[4]:.1f} chars")
    print(f"  Average definition length: {stats[5]:.1f} chars")
    
    # Search examples
    print(f"\nSEARCH EXAMPLES:")
    
    # Names containing "bread"
    cursor.execute("SELECT common_name FROM cfcs_cname WHERE common_name LIKE '%bread%' LIMIT 5")
    bread_names = cursor.fetchall()
    if bread_names:
        print(f"  Bread-related names: {[name[0] for name in bread_names]}")
    
    # Names containing "milk"
    cursor.execute("SELECT common_name FROM cfcs_cname WHERE common_name LIKE '%milk%' LIMIT 5")
    milk_names = cursor.fetchall()
    if milk_names:
        print(f"  Milk-related names: {[name[0] for name in milk_names]}")
    
    # Names containing "cheese"
    cursor.execute("SELECT common_name FROM cfcs_cname WHERE common_name LIKE '%cheese%' LIMIT 5")
    cheese_names = cursor.fetchall()
    if cheese_names:
        print(f"  Cheese-related names: {[name[0] for name in cheese_names]}")
    
    conn.close()

if __name__ == "__main__":
    create_cfcs_cname_table()
    print("\n" + "="*60)
    print("Want to view statistics? Uncomment the line below:")
    print("# view_cfcs_cname_stats()")
    # view_cfcs_cname_stats()