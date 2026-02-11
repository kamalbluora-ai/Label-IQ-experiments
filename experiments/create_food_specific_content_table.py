import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

def create_food_specific_content_table():
    """Create and populate food_specific_labelling_requirements_content table from all Food-specific requirements content.json files"""
    
    # Paths
    food_specific_dir = Path("industry_labelling_tool_parsed/Food_specific_labelling_requirements")
    db_file = Path("ilt_requirements.db")
    
    # Connect to SQLite database
    if not db_file.exists():
        print(f"Error: Database {db_file} does not exist!")
        print("Please run create_ilt_database.py first.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"Creating food_specific_labelling_requirements_content table in: {db_file}")
    
    # Create food_specific_labelling_requirements_content table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS food_specific_labelling_requirements_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requirement_id INTEGER,
        requirement_name TEXT NOT NULL,
        section TEXT NOT NULL,
        content TEXT,
        internal_links TEXT,
        external_links TEXT,
        source_url TEXT,
        created_date DATETIME NOT NULL,
        FOREIGN KEY (requirement_id) REFERENCES food_specific_labelling_requirements(id)
    )
    """
    
    cursor.execute(create_table_sql)
    print("Table 'food_specific_labelling_requirements_content' created/verified")
    
    # Check if external_links column exists, if not add it
    cursor.execute("PRAGMA table_info(food_specific_labelling_requirements_content)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'external_links' not in columns:
        print("Adding external_links column to food_specific_labelling_requirements_content")
        cursor.execute("ALTER TABLE food_specific_labelling_requirements_content ADD COLUMN external_links TEXT")
    
    if 'source_url' not in columns:
        print("Adding source_url column to food_specific_labelling_requirements_content")
        cursor.execute("ALTER TABLE food_specific_labelling_requirements_content ADD COLUMN source_url TEXT")
    
    # Clear existing data and reset sequence
    cursor.execute("DELETE FROM food_specific_labelling_requirements_content")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='food_specific_labelling_requirements_content'")
    conn.commit()
    print("Existing data cleared and sequence reset")
    
    # Get all requirement names from food_specific_labelling_requirements table
    cursor.execute("SELECT id, requirement FROM food_specific_labelling_requirements ORDER BY id")
    requirements = cursor.fetchall()
    
    if not requirements:
        print("Error: No requirements found in food_specific_labelling_requirements table")
        conn.close()
        return
    
    print(f"Found {len(requirements)} requirements to process:")
    for req_id, req_name in requirements:
        print(f"  {req_id}: {req_name}")
    
    total_records_inserted = 0
    created_date = datetime.utcnow()
    
    # Process each requirement
    for requirement_id, requirement_name in requirements:
        print(f"\nProcessing requirement: {requirement_name}")
        
        # Construct path to content.json file
        requirement_folder = requirement_name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace(',', '').replace('-', '_')
        content_json_file = food_specific_dir / requirement_folder / "content.json"
        external_links_json_file = food_specific_dir / requirement_folder / "external_links.json"
        
        print(f"Looking for: {content_json_file}")
        
        if not content_json_file.exists():
            print(f"  Warning: {content_json_file} not found - skipping")
            continue
        
        # Load content JSON data
        try:
            with open(content_json_file, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  Error parsing JSON for {requirement_name}: {e}")
            continue
        
        # Extract source_url from content data
        source_url = content_data.get('source_url', '')
        print(f"  Source URL: {source_url}")
        
        # Load external links JSON data
        external_links_data = {}
        if external_links_json_file.exists():
            try:
                with open(external_links_json_file, 'r', encoding='utf-8') as f:
                    external_links_data = json.load(f)
                print(f"  External links file found")
            except json.JSONDecodeError as e:
                print(f"  Warning: Error parsing external_links.json for {requirement_name}: {e}")
        else:
            print(f"  No external_links.json found for {requirement_name}")
        
        # Extract all external link hrefs
        external_hrefs = []
        if 'external_links' in external_links_data:
            external_links_array = external_links_data['external_links']
            for link_data in external_links_array:
                if isinstance(link_data, dict) and 'href' in link_data:
                    external_hrefs.append(link_data['href'])
        
        external_links_text = ', '.join(external_hrefs) if external_hrefs else None
        
        # Process sections from content.json
        sections = content_data.get('sections', {})
        records_inserted_for_requirement = 0
        
        for section_name, section_data in sections.items():
            print(f"  Processing section: {section_name}")
            
            # Concatenate content array into single text
            content_array = section_data.get('content', [])
            content_text = ' '.join(content_array) if content_array else None
            
            # Concatenate internal links hrefs
            internal_links_array = section_data.get('internal_links', [])
            internal_links_hrefs = [link.get('href', '') for link in internal_links_array if link.get('href')]
            internal_links_text = ', '.join(internal_links_hrefs) if internal_links_hrefs else None
            
            # Insert record
            insert_sql = """
            INSERT INTO food_specific_labelling_requirements_content 
            (requirement_id, requirement_name, section, content, internal_links, external_links, source_url, created_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_sql, (
                requirement_id, 
                requirement_name, 
                section_name, 
                content_text, 
                internal_links_text,
                external_links_text,
                source_url, 
                created_date
            ))
            records_inserted_for_requirement += 1
            total_records_inserted += 1
            
            print(f"    Content length: {len(content_text) if content_text else 0} chars")
            print(f"    Internal links: {len(internal_links_hrefs)} links")
            print(f"    External links: {len(external_hrefs)} links")
        
        print(f"  Inserted {records_inserted_for_requirement} sections for {requirement_name}")
    
    # Commit changes
    conn.commit()
    
    print(f"\nTotal records inserted: {total_records_inserted}")
    
    # Display summary
    print(f"\n{'='*60}")
    print("TABLE SUMMARY")
    print(f"{'='*60}")
    
    cursor.execute("SELECT COUNT(*) FROM food_specific_labelling_requirements_content")
    total_records = cursor.fetchone()[0]
    print(f"Total records in food_specific_labelling_requirements_content: {total_records}")
    
    # Summary by requirement
    cursor.execute("""
    SELECT requirement_name, COUNT(*) as section_count
    FROM food_specific_labelling_requirements_content 
    GROUP BY requirement_name 
    ORDER BY requirement_id
    """)
    
    print(f"\nRECORDS BY REQUIREMENT:")
    for req_name, section_count in cursor.fetchall():
        print(f"  {req_name}: {section_count} sections")
    
    # Show sample records
    print(f"\n{'='*60}")
    print("SAMPLE RECORDS")
    print(f"{'='*60}")
    
    cursor.execute("""
    SELECT id, requirement_name, section, 
           SUBSTR(content, 1, 80) as content_preview,
           SUBSTR(internal_links, 1, 60) as internal_links_preview,
           SUBSTR(external_links, 1, 60) as external_links_preview,
           source_url
    FROM food_specific_labelling_requirements_content 
    ORDER BY id
    LIMIT 10
    """)
    
    sample_records = cursor.fetchall()
    for record in sample_records:
        print(f"ID: {record[0]}")
        print(f"Requirement: {record[1]}")
        print(f"Section: {record[2]}")
        print(f"Content Preview: {record[3]}...")
        print(f"Internal Links Preview: {record[4]}...")
        print(f"External Links Preview: {record[5]}...")
        print(f"Source URL: {record[6]}")
        print("-" * 40)
    
    conn.close()
    print(f"\nDatabase updated successfully!")

def view_food_specific_content_stats():
    """Optional: View statistics about the food_specific_labelling_requirements_content table"""
    db_file = Path("ilt_requirements.db")
    
    if not db_file.exists():
        print("Database not found.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='food_specific_labelling_requirements_content'")
    if not cursor.fetchone():
        print("Table 'food_specific_labelling_requirements_content' does not exist.")
        conn.close()
        return
    
    # Content statistics by requirement
    print("\nFOOD-SPECIFIC CONTENT STATISTICS BY REQUIREMENT:")
    cursor.execute("""
    SELECT 
        requirement_name,
        COUNT(*) as section_count,
        AVG(LENGTH(content)) as avg_content_length,
        SUM(CASE WHEN internal_links IS NOT NULL THEN 1 ELSE 0 END) as sections_with_internal_links,
        SUM(CASE WHEN external_links IS NOT NULL THEN 1 ELSE 0 END) as sections_with_external_links
    FROM food_specific_labelling_requirements_content 
    GROUP BY requirement_name, requirement_id
    ORDER BY requirement_id
    """)
    
    for row in cursor.fetchall():
        req_name, section_count, avg_content, sections_with_internal_links, sections_with_external_links = row
        print(f"  {req_name}:")
        print(f"    Sections: {section_count}")
        print(f"    Avg content length: {avg_content:.0f} chars")
        print(f"    Sections with internal links: {sections_with_internal_links}")
        print(f"    Sections with external links: {sections_with_external_links}")
        print()
    
    # Overall statistics
    cursor.execute("""
    SELECT 
        COUNT(DISTINCT requirement_name) as total_requirements,
        COUNT(*) as total_sections,
        AVG(LENGTH(content)) as avg_content_length,
        SUM(CASE WHEN internal_links IS NOT NULL THEN 1 ELSE 0 END) as sections_with_internal_links,
        SUM(CASE WHEN external_links IS NOT NULL THEN 1 ELSE 0 END) as sections_with_external_links
    FROM food_specific_labelling_requirements_content
    """)
    
    stats = cursor.fetchone()
    print(f"OVERALL FOOD-SPECIFIC STATISTICS:")
    print(f"  Total requirements processed: {stats[0]}")
    print(f"  Total sections: {stats[1]}")
    print(f"  Average content length: {stats[2]:.0f} chars")
    print(f"  Sections with internal links: {stats[3]}")
    print(f"  Sections with external links: {stats[4]}")
    
    conn.close()

if __name__ == "__main__":
    create_food_specific_content_table()
    print("\n" + "="*60)
    print("Want to view statistics? Uncomment the line below:")
    print("# view_food_specific_content_stats()")
    # view_food_specific_content_stats()