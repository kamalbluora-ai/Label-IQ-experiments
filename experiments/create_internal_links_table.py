import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

def create_internal_links_table():
    """Create and populate internal_links table from all content.json files"""
    
    # Paths
    base_dir = Path("industry_labelling_tool_parsed")
    db_file = Path("ilt_requirements.db")
    
    # Connect to SQLite database
    if not db_file.exists():
        print(f"Error: Database {db_file} does not exist!")
        print("Please run create_ilt_database.py first.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"Creating internal_links table in: {db_file}")
    
    # Create internal_links table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS internal_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link TEXT NOT NULL,
        link_text TEXT NOT NULL,
        context_text TEXT,
        section TEXT NOT NULL,
        tag TEXT NOT NULL,
        created_date DATETIME NOT NULL
    )
    """
    
    cursor.execute(create_table_sql)
    print("Table 'internal_links' created/verified")
    
    # Clear existing data and reset sequence
    cursor.execute("DELETE FROM internal_links")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='internal_links'")
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
                
            content_json_file = requirement_dir / "content.json"
            
            if not content_json_file.exists():
                print(f"  Warning: {content_json_file} not found - skipping")
                continue
                
            # Create tag for this requirement
            requirement_name = requirement_dir.name.lower()
            tag = f"{category_tag}.{requirement_name}"
            
            print(f"  Processing: {requirement_dir.name}")
            
            # Load content JSON data
            try:
                with open(content_json_file, 'r', encoding='utf-8') as f:
                    content_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"    Error parsing JSON: {e}")
                continue
            
            # Process sections and their internal links
            sections = content_data.get('sections', {})
            records_for_requirement = 0
            
            for section_name, section_data in sections.items():
                internal_links = section_data.get('internal_links', [])
                
                for link_data in internal_links:
                    link_href = link_data.get('href', '')
                    link_text = link_data.get('link_text', '')
                    context_text = link_data.get('context_text', '')
                    
                    if not link_href or not link_text:
                        continue
                        
                    # Insert record
                    insert_sql = """
                    INSERT INTO internal_links (link, link_text, context_text, section, tag, created_date) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    """
                    cursor.execute(insert_sql, (
                        link_href,
                        link_text,
                        context_text,
                        section_name,
                        tag,
                        created_date
                    ))
                    records_for_requirement += 1
                    total_records_inserted += 1
            
            print(f"    Inserted {records_for_requirement} internal links")
    
    # Commit changes
    conn.commit()
    
    print(f"\nTotal internal links inserted: {total_records_inserted}")
    
    # Display summary
    print(f"\n{'='*60}")
    print("INTERNAL LINKS TABLE SUMMARY")
    print(f"{'='*60}")
    
    cursor.execute("SELECT COUNT(*) FROM internal_links")
    total_records = cursor.fetchone()[0]
    print(f"Total records in internal_links: {total_records}")
    
    # Summary by tag (category)
    cursor.execute("""
    SELECT tag, COUNT(*) as link_count
    FROM internal_links 
    GROUP BY tag 
    ORDER BY tag
    """)
    
    print(f"\nINTERNAL LINKS BY REQUIREMENT:")
    for tag, link_count in cursor.fetchall():
        print(f"  {tag}: {link_count} links")
    
    # Show sample records
    print(f"\n{'='*60}")
    print("SAMPLE INTERNAL LINKS")
    print(f"{'='*60}")
    
    cursor.execute("""
    SELECT id, link, link_text, section, tag,
           SUBSTR(context_text, 1, 80) as context_preview
    FROM internal_links 
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
    print(f"\nInternal links table updated successfully!")

def view_internal_links_stats():
    """Optional: View statistics about the internal_links table"""
    db_file = Path("ilt_requirements.db")
    
    if not db_file.exists():
        print("Database not found.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='internal_links'")
    if not cursor.fetchone():
        print("Table 'internal_links' does not exist.")
        conn.close()
        return
    
    # Statistics by category
    print("\nINTERNAL LINKS STATISTICS BY CATEGORY:")
    cursor.execute("""
    SELECT 
        SUBSTR(tag, 1, INSTR(tag, '.') - 1) as category,
        COUNT(*) as total_links,
        COUNT(DISTINCT tag) as requirements_count,
        AVG(LENGTH(context_text)) as avg_context_length
    FROM internal_links 
    GROUP BY SUBSTR(tag, 1, INSTR(tag, '.') - 1)
    ORDER BY category
    """)
    
    for row in cursor.fetchall():
        category, total_links, req_count, avg_context = row
        print(f"  {category}:")
        print(f"    Total links: {total_links}")
        print(f"    Requirements: {req_count}")
        print(f"    Avg context length: {avg_context:.0f} chars")
        print()
    
    # Most common link domains
    print("TOP 10 MOST COMMON LINK DOMAINS:")
    cursor.execute("""
    SELECT 
        CASE 
            WHEN link LIKE '%inspection.canada.ca%' THEN 'inspection.canada.ca'
            WHEN link LIKE '%canada.ca%' THEN 'canada.ca'
            WHEN link LIKE '%ic.gc.ca%' THEN 'ic.gc.ca'
            ELSE 'other'
        END as domain,
        COUNT(*) as count
    FROM internal_links 
    GROUP BY domain
    ORDER BY count DESC
    LIMIT 10
    """)
    
    for domain, count in cursor.fetchall():
        print(f"  {domain}: {count} links")
    
    conn.close()

if __name__ == "__main__":
    create_internal_links_table()
    print("\n" + "="*60)
    print("Want to view statistics? Uncomment the line below:")
    print("# view_internal_links_stats()")
    # view_internal_links_stats()