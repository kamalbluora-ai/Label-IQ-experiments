import requests
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from bs4 import BeautifulSoup
import re, config

def create_csiv_cname_table():
    """Create and populate csiv_cname table from Canadian Standards of Identity volumes 1-8"""
    
    # Base URL pattern for CSI volumes
    base_url = "https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference/canadian-standards-identity-volume-{}"
    
    # All 8 volumes to process
    volumes_to_process = [
        {"num": 1, "url": base_url.format("1")},
        {"num": 2, "url": base_url.format("2")}, 
        {"num": 3, "url": base_url.format("3")},
        {"num": 4, "url": base_url.format("4")},
        {"num": 5, "url": base_url.format("5")},
        {"num": 6, "url": base_url.format("6")},
        {"num": 7, "url": base_url.format("7")},
        {"num": 8, "url": base_url.format("8")}
    ]
    
    db_file = Path("ilt_requirements.db")
    
    # OpenAI Client
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
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
    
    print(f"Creating csiv_cname table in: {db_file}")
    
    # Drop existing table to avoid schema conflicts
    cursor.execute("DROP TABLE IF EXISTS csiv_cname")
    print("Dropped existing csiv_cname table (if it existed)")
    
    # Create csiv_cname table
    create_table_sql = """
    CREATE TABLE csiv_cname (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        common_name TEXT NOT NULL,
        definition TEXT,
        volume_number INTEGER,
        volume_title TEXT,
        section TEXT,
        tag TEXT,
        source_url TEXT,
        created_date DATETIME NOT NULL
    )
    """
    
    cursor.execute(create_table_sql)
    print("Table 'csiv_cname' created with new schema")
    
    # Reset sequence
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='csiv_cname'")
    conn.commit()
    print("Database changes committed")
    
    # Process each volume
    all_extracted_data = []
    
    for volume_info in volumes_to_process:
        vol_num = volume_info["num"]
        vol_url = volume_info["url"]
        
        print(f"\n{'='*60}")
        print(f"PROCESSING VOLUME {vol_num}")
        print(f"{'='*60}")
        print(f"URL: {vol_url}")
        
        # Fetch the webpage
        try:
            print(f"Fetching Volume {vol_num} webpage...")
            response = requests.get(vol_url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            print("Webpage fetched successfully")
        except requests.RequestException as e:
            print(f"Error fetching Volume {vol_num} webpage: {e}")
            print(f"Skipping Volume {vol_num}")
            continue
        
        # Extract common names using OpenAI GPT
        print(f"Extracting common names from Volume {vol_num} using OpenAI GPT...")
        try:
            volume_data = extract_csi_names_with_gpt(client, html_content, vol_num, vol_url)
            print(f"Extracted {len(volume_data)} common names from Volume {vol_num}")
            
            if volume_data:
                all_extracted_data.extend(volume_data)
            else:
                print(f"No data extracted from Volume {vol_num}. Check GPT response.")
                
        except Exception as e:
            print(f"Error extracting data from Volume {vol_num}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print("INSERTING DATA INTO DATABASE")
    print(f"{'='*60}")
    
    if not all_extracted_data:
        print("No data extracted from any volume. Exiting.")
        conn.close()
        return
    
    # Insert results into database
    records_inserted = 0
    created_date = datetime.now()
    
    for item in all_extracted_data:
        try:
            insert_sql = """
            INSERT INTO csiv_cname (common_name, definition, volume_number, volume_title, section, tag, source_url, created_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_sql, (
                item.get("common_name", ""),
                item.get("definition", ""),
                item.get("volume_number", 0),
                item.get("volume_title", ""),
                item.get("section", ""),
                item.get("tag", ""),
                item.get("source_url", ""),
                created_date
            ))
            records_inserted += 1
            
            # Show progress every 50 records
            if records_inserted % 50 == 0:
                print(f"  Inserted {records_inserted} records...")
                
        except Exception as e:
            print(f"Error inserting record: {e}")
            continue
    
    # Commit changes
    conn.commit()
    
    print(f"\nTotal records inserted: {records_inserted}")
    
    # Display summary
    print(f"\n{'='*60}")
    print("CANADIAN STANDARDS OF IDENTITY TABLE SUMMARY")
    print(f"{'='*60}")
    
    cursor.execute("SELECT COUNT(*) FROM csiv_cname")
    total_records = cursor.fetchone()[0]
    print(f"Total records in csiv_cname: {total_records}")
    
    # Summary by volume
    cursor.execute("""
    SELECT volume_number, volume_title, COUNT(*) as name_count
    FROM csiv_cname 
    WHERE volume_number IS NOT NULL
    GROUP BY volume_number, volume_title
    ORDER BY volume_number
    """)
    
    print(f"\nCOMMON NAMES BY VOLUME:")
    for vol_num, vol_title, name_count in cursor.fetchall():
        print(f"  Volume {vol_num} - {vol_title}: {name_count} names")
    
    # Summary by section
    cursor.execute("""
    SELECT section, COUNT(*) as name_count
    FROM csiv_cname 
    WHERE section IS NOT NULL AND section != ''
    GROUP BY section 
    ORDER BY name_count DESC
    LIMIT 10
    """)
    
    print(f"\nTOP 10 SECTIONS:")
    for section, name_count in cursor.fetchall():
        print(f"  {section}: {name_count} names")
    
    # Show sample records
    print(f"\n{'='*60}")
    print("SAMPLE COMMON NAMES")
    print(f"{'='*60}")
    
    cursor.execute("""
    SELECT id, common_name, volume_number, volume_title, section,
           SUBSTR(definition, 1, 60) as definition_preview
    FROM csiv_cname 
    ORDER BY volume_number, id
    LIMIT 15
    """)
    
    sample_records = cursor.fetchall()
    for record in sample_records:
        print(f"ID: {record[0]}")
        print(f"Common Name: {record[1]}")
        print(f"Volume: {record[2]} - {record[3]}")
        print(f"Section: {record[4]}")
        print(f"Definition Preview: {record[5]}...")
        print("-" * 40)
    
    conn.close()
    print(f"\nCanadian Standards of Identity table updated successfully!")
    
    # Final validation
    print(f"\n{'='*60}")
    print("VOLUME COVERAGE VALIDATION")
    print(f"{'='*60}")
    
    validate_csi_coverage(db_file)

def extract_csi_names_with_gpt(client, html_content, volume_number, source_url):
    """Extract common names from CSI HTML using OpenAI GPT with chunking"""
    
    # First, extract and clean the main content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, style, and other non-content elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    # Find main content
    main_content = soup.find('main') or soup.find('div', class_='container') or soup
    
    # Extract clean text content
    clean_text = main_content.get_text(separator='\n', strip=True)
    
    print(f"  Volume {volume_number} content length: {len(clean_text)} characters")
    
    # Improved chunking strategy for CSI content
    max_chunk_size = 15000
    overlap_size = 3000
    chunks = []
    
    start = 0
    while start < len(clean_text):
        end = start + max_chunk_size
        
        if end < len(clean_text):
            # Look for good break points
            search_start = max(start + max_chunk_size - overlap_size, start)
            
            break_patterns = [
                r'\n\d+\.\d+\.\d+',       # Section numbers (e.g., 1.2.3)
                r'\n\d+\.\d+',            # Section numbers (e.g., 1.2)
                r'\n[A-Z][a-z]+ [A-Z]',   # Food names starting sentences
                r'\n\s*\n',               # Double newlines
            ]
            
            best_break = end
            for pattern in break_patterns:
                matches = list(re.finditer(pattern, clean_text[search_start:end + overlap_size]))
                if matches:
                    last_match = matches[-1]
                    potential_break = search_start + last_match.start()
                    if potential_break > start + max_chunk_size // 2:
                        best_break = potential_break
                        break
            
            end = min(best_break, len(clean_text))
        
        chunk = clean_text[start:end].strip()
        if chunk and len(chunk) > 100:
            chunks.append(chunk)
            print(f"    Chunk {len(chunks)}: {len(chunk)} chars")
        
        start = end
        
        if start >= len(clean_text):
            break
    
    print(f"  Split Volume {volume_number} into {len(chunks)} chunks")
    
    # Process each chunk
    all_extracted_data = []
    
    for i, chunk in enumerate(chunks):
        print(f"  Processing Volume {volume_number} chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
        
        system_prompt = f"""You are an expert parser for the Canadian Standards of Identity Volume {volume_number}.

Extract common names from the text. A common name is a food/product name that has a standard definition.

IMPORTANT RULES:
1. Extract COMPLETE food/product names including all variations
2. For compound names like "Butter or Dairy Butter" - extract as TWO separate entries
3. Clean section numbers but keep the full product name
4. Focus on products that have identity standards

For each product name found, extract:
- common_name: the actual product name (complete name, no section numbers)
- definition: the standard definition that follows the name (first sentence is enough)
- volume_number: {volume_number}
- volume_title: the volume title if mentioned
- section: the section number (e.g. "1.2" or "3.1.4")
- tag: the section heading if available

Return ONLY a pipe-delimited format with one product per line:
common_name|definition|volume_number|volume_title|section|tag

Example:
Butter|is the food derived exclusively from milk fat|{volume_number}|Volume {volume_number} - Dairy Products|1.2|1.2 Butter Standards

IMPORTANT: Only extract actual product names with standards, not section headings or navigation text.
No headers, no extra text."""

        user_prompt = f"""Extract product common names from this Canadian Standards of Identity Volume {volume_number} text chunk.

{chunk}

Return ONLY pipe-delimited data, one product per line:
common_name|definition|volume_number|volume_title|section|tag"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=16000
            )

            content = response.choices[0].message.content.strip()
            finish_reason = response.choices[0].finish_reason
            
            if finish_reason == "length":
                print(f"    WARNING: Response truncated for Volume {volume_number} chunk {i+1}")
            
            # Parse pipe-delimited format into JSON objects
            parsed_data = []
            
            try:
                lines = content.strip().split('\n')
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line or line.startswith('#') or '|' not in line:
                        continue
                    
                    parts = line.split('|')
                    if len(parts) >= 6:
                        common_name = parts[0].strip()
                        definition = parts[1].strip()
                        vol_num = parts[2].strip()
                        vol_title = parts[3].strip()
                        section = parts[4].strip()
                        tag = parts[5].strip()
                        
                        if common_name and len(common_name) > 2:
                            item = {
                                "common_name": common_name,
                                "definition": definition,
                                "volume_number": volume_number,  # Use the actual volume number
                                "volume_title": vol_title,
                                "section": section,
                                "tag": tag,
                                "source_url": source_url
                            }
                            parsed_data.append(item)
                    else:
                        if finish_reason == "length" and line_num == len(lines):
                            print(f"    Skipping incomplete last line due to truncation: {line[:50]}...")
                        else:
                            print(f"    Skipping malformed line {line_num}: {line[:50]}...")
                
                print(f"    Successfully parsed {len(parsed_data)} items from Volume {volume_number} chunk {i+1}")
                
            except Exception as parse_error:
                print(f"    Error parsing pipe-delimited format: {parse_error}")
                continue
            
            all_extracted_data.extend(parsed_data)
            
        except Exception as e:
            print(f"    Error processing Volume {volume_number} chunk {i+1}: {e}")
            continue
    
    print(f"  Total extracted items from Volume {volume_number}: {len(all_extracted_data)}")
    
    # Remove duplicates based on common_name (case-insensitive)
    seen_names = set()
    unique_data = []
    
    for item in all_extracted_data:
        name_lower = item["common_name"].lower()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique_data.append(item)
    
    print(f"  After removing duplicates: {len(unique_data)} unique items from Volume {volume_number}")
    
    return unique_data

def validate_csi_coverage(db_file):
    """Validate CSI volume coverage"""
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check coverage for all 8 volumes
    expected_volumes = list(range(1, 9))  # Volumes 1-8
    
    cursor.execute("SELECT DISTINCT volume_number FROM csiv_cname WHERE volume_number IS NOT NULL ORDER BY volume_number")
    covered_volumes = [row[0] for row in cursor.fetchall()]
    
    print(f"Expected volumes: {expected_volumes}")
    print(f"Covered volumes: {covered_volumes}")
    
    missing_volumes = [vol for vol in expected_volumes if vol not in covered_volumes]
    
    if missing_volumes:
        print(f"❌ Missing volumes: {missing_volumes}")
    else:
        print("✅ All 8 volumes covered!")
    
    # Volume statistics
    for vol_num in covered_volumes:
        cursor.execute("SELECT COUNT(*) FROM csiv_cname WHERE volume_number = ?", (vol_num,))
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT volume_title FROM csiv_cname WHERE volume_number = ? LIMIT 1", (vol_num,))
        title_row = cursor.fetchone()
        title = title_row[0] if title_row else "Unknown"
        
        status = "✅" if count > 0 else "❌"
        print(f"  {status} Volume {vol_num} ({title}): {count} common names")
    
    conn.close()

def view_csiv_cname_stats():
    """Optional: View statistics about the csiv_cname table"""
    db_file = Path("ilt_requirements.db")
    
    if not db_file.exists():
        print("Database not found.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='csiv_cname'")
    if not cursor.fetchone():
        print("Table 'csiv_cname' does not exist.")
        conn.close()
        return
    
    # Content statistics
    print("\nCANADIAN STANDARDS OF IDENTITY STATISTICS:")
    
    cursor.execute("""
    SELECT 
        COUNT(*) as total_names,
        COUNT(CASE WHEN definition IS NOT NULL AND definition != '' THEN 1 END) as names_with_def,
        COUNT(CASE WHEN volume_title IS NOT NULL AND volume_title != '' THEN 1 END) as names_with_volume,
        COUNT(CASE WHEN section IS NOT NULL AND section != '' THEN 1 END) as names_with_section,
        AVG(LENGTH(common_name)) as avg_name_length,
        AVG(LENGTH(definition)) as avg_def_length
    FROM csiv_cname
    """)
    
    stats = cursor.fetchone()
    print(f"  Total common names: {stats[0]}")
    print(f"  Names with definitions: {stats[1]}")
    print(f"  Names with volume info: {stats[2]}")
    print(f"  Names with sections: {stats[3]}")
    print(f"  Average name length: {stats[4]:.1f} chars")
    print(f"  Average definition length: {stats[5]:.1f} chars")
    
    # Search examples
    print(f"\nSEARCH EXAMPLES:")
    
    # Names containing "milk"
    cursor.execute("SELECT common_name FROM csiv_cname WHERE common_name LIKE '%milk%' LIMIT 5")
    milk_names = cursor.fetchall()
    if milk_names:
        print(f"  Milk-related names: {[name[0] for name in milk_names]}")
    
    # Names containing "bread"
    cursor.execute("SELECT common_name FROM csiv_cname WHERE common_name LIKE '%bread%' LIMIT 5")
    bread_names = cursor.fetchall()
    if bread_names:
        print(f"  Bread-related names: {[name[0] for name in bread_names]}")
    
    conn.close()

if __name__ == "__main__":
    create_csiv_cname_table()
    print("\n" + "="*60)
    print("Want to view statistics? Uncomment the line below:")
    print("# view_csiv_cname_stats()")
    # view_csiv_cname_stats()