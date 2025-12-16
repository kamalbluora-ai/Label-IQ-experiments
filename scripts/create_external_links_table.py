import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

def create_external_links_table():
    """Create and populate external_links table from all external_links.json files"""
    
    # Paths
    base_dir = Path("industry_labelling_tool_parsed")
    db_file = Path(__file__).parent.parent / "data" / "ilt_requirements.db"
    
    # Connect to SQLite database
    if not db_file.exists():
        print(f"Error: Database {db_file} does not exist!")
        print("Please run create_ilt_database.py first.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"Creating external_links table in: {db_file}")
    
    # Create external_links table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS external_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link TEXT NOT NULL,
        link_text TEXT,
        context_text TEXT,
        section TEXT,
        tag TEXT NOT NULL,
        created_date DATETIME NOT NULL
    )
    """
    
    cursor.execute(create_table_sql)
    print("Table 'external_links' created/verified")
    
    # Clear existing data and reset sequence
    cursor.execute("DELETE FROM external_links")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='external_links'")
    conn.commit()
    print("Existing data cleared and sequence reset")
    
    # Define the main categories and their directories
    categories = [
        ("Core_labelling_requirements", "core_labelling_requirements"),
        ("Claims_and_statements", "claims_and_statements"), 
        ("Food_specific_labelling_requirements", "food_specific_labelling_requirements")
    ]
    
    total_records_inserted = 0
    created_date = datetime.utcnow()
    
    # Process each category
    for dir_name, category_tag in categories:
        category_dir = base_dir / dir_name
        
        if not category_dir.exists():
            print(f"Warning: Directory {category_dir} not found - skipping")
            continue
            
        print(f"\nProcessing category: {dir_name}")
        
        # Get all subdirectories in this category
        for requirement_dir in category_dir.iterdir():
            if not requirement_dir.is_dir():
                continue
                
            external_links_json_file = requirement_dir / "external_links.json"
            
            if not external_links_json_file.exists():
                print(f"  Warning: {external_links_json_file} not found - skipping")
                continue
                
            # Create tag for this requirement
            requirement_name = requirement_dir.name.lower()
            tag = f"{category_tag}.{requirement_name}"
            
            print(f"  Processing: {requirement_dir.name}")
            
            # Load external links JSON data
            try:
                with open(external_links_json_file, 'r', encoding='utf-8') as f:
                    external_links_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"    Error parsing JSON: {e}")
                continue
            
            # Process external links array
            external_links_array = external_links_data.get('external_links', [])
            records_for_requirement = 0
            
            for link_data in external_links_array:
                # Handle different possible structures
                if isinstance(link_data, dict):
                    link_href = link_data.get('href', '')
                    link_text = link_data.get('text', '') or link_data.get('link_text', '')
                    context_text = link_data.get('context_text', '') or link_data.get('context', '')
                    section = link_data.get('section', '') or link_data.get('section_name', '')
                elif isinstance(link_data, str):
                    # If it's just a string URL
                    link_href = link_data
                    link_text = ''
                    context_text = ''
                    section = ''
                else:
                    continue
                
                if not link_href:
                    continue
                    
                # Insert record
                insert_sql = """
                INSERT INTO external_links (link, link_text, context_text, section, tag, created_date) 
                VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(insert_sql, (
                    link_href,
                    link_text,
                    context_text,
                    section,
                    tag,
                    created_date
                ))
                records_for_requirement += 1
                total_records_inserted += 1
            
            print(f"    Inserted {records_for_requirement} external links")
    
    # Commit changes
    conn.commit()
    
    print(f"\nTotal external links inserted: {total_records_inserted}")
    
    # Display summary
    print(f"\n{'='*60}")
    print("EXTERNAL LINKS TABLE SUMMARY")
    print(f"{'='*60}")
    
    cursor.execute("SELECT COUNT(*) FROM external_links")
    total_records = cursor.fetchone()[0]
    print(f"Total records in external_links: {total_records}")
    
    # Summary by tag (category)
    cursor.execute("""
    SELECT tag, COUNT(*) as link_count
    FROM external_links 
    GROUP BY tag 
    ORDER BY tag
    """)
    
    print(f"\nEXTERNAL LINKS BY REQUIREMENT:")
    for tag, link_count in cursor.fetchall():
        print(f"  {tag}: {link_count} links")
    
    # Show sample records
    print(f"\n{'='*60}")
    print("SAMPLE EXTERNAL LINKS")
    print(f"{'='*60}")
    
    cursor.execute("""
    SELECT id, link, link_text, section, tag,
           SUBSTR(context_text, 1, 80) as context_preview
    FROM external_links 
    ORDER BY id
    LIMIT 10
    """)
    
    sample_records = cursor.fetchall()
    for record in sample_records:
        print(f"ID: {record[0]}")
        print(f"Link: {record[1]}")
        print(f"Link Text: {record[2]}")
        print(f"Section: {record[3]}")
        print(f"Tag: {record[4]}")
        print(f"Context Preview: {record[5]}...")
        print("-" * 40)
    
    conn.close()
    print(f"\nExternal links table updated successfully!")

def view_external_links_stats():
    """Optional: View statistics about the external_links table"""
    db_file = Path(__file__).parent.parent / "data" / "ilt_requirements.db"
    
    if not db_file.exists():
        print("Database not found.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='external_links'")
    if not cursor.fetchone():
        print("Table 'external_links' does not exist.")
        conn.close()
        return
    
    # Statistics by category
    print("\nEXTERNAL LINKS STATISTICS BY CATEGORY:")
    cursor.execute("""
    SELECT 
        SUBSTR(tag, 1, INSTR(tag, '.') - 1) as category,
        COUNT(*) as total_links,
        COUNT(DISTINCT tag) as requirements_count,
        COUNT(CASE WHEN link_text != '' THEN 1 END) as links_with_text
    FROM external_links 
    GROUP BY SUBSTR(tag, 1, INSTR(tag, '.') - 1)
    ORDER BY category
    """)
    
    for row in cursor.fetchall():
        category, total_links, req_count, links_with_text = row
        print(f"  {category}:")
        print(f"    Total links: {total_links}")
        print(f"    Requirements: {req_count}")
        print(f"    Links with text: {links_with_text}")
        print()
    
    # Most common external domains
    print("TOP 10 MOST COMMON EXTERNAL DOMAINS:")
    cursor.execute("""
    SELECT 
        CASE 
            WHEN link LIKE '%canada.ca%' THEN 'canada.ca'
            WHEN link LIKE '%gc.ca%' THEN 'gc.ca'
            WHEN link LIKE '%fao.org%' THEN 'fao.org'
            WHEN link LIKE '%codexalimentarius.org%' THEN 'codexalimentarius.org'
            WHEN link LIKE '%who.int%' THEN 'who.int'
            WHEN link LIKE '%iso.org%' THEN 'iso.org'
            WHEN link LIKE '%oecd.org%' THEN 'oecd.org'
            ELSE SUBSTR(link, INSTR(link, '//') + 2, INSTR(SUBSTR(link, INSTR(link, '//') + 2), '/') - 1)
        END as domain,
        COUNT(*) as count
    FROM external_links 
    GROUP BY domain
    ORDER BY count DESC
    LIMIT 10
    """)
    
    for domain, count in cursor.fetchall():
        print(f"  {domain}: {count} links")
    
    # Links without text
    cursor.execute("SELECT COUNT(*) FROM external_links WHERE link_text = '' OR link_text IS NULL")
    no_text_count = cursor.fetchone()[0]
    print(f"\nLinks without descriptive text: {no_text_count}")
    
    conn.close()

if __name__ == "__main__":
    create_external_links_table()
    print("\n" + "="*60)
    print("Want to view statistics? Uncomment the line below:")
    print("# view_external_links_stats()")
    # view_external_links_stats()