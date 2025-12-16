import json
import sqlite3
from datetime import datetime
from pathlib import Path

def create_requirements_checklist_table():
    """Create and populate requirements_checklist table from cfia_rules.json"""
    
    # Paths
    json_file = Path("food_labelling_requirements_checklist/cfia_rules.json")
    db_file = Path(__file__).parent.parent.parent / "data" / "ilt_requirements.db"
    
    # Load JSON data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_file} not found!")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return
    
    # Get generated_at datetime
    generated_at = data.get('generated_at', datetime.utcnow().isoformat() + 'Z')
    # Convert to datetime object for SQLite
    try:
        created_date = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
    except:
        created_date = datetime.utcnow()
    
    # Connect to SQLite database
    if not db_file.exists():
        print(f"Error: Database {db_file} does not exist!")
        print("Please run create_ilt_database.py first.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"Adding requirements_checklist table to: {db_file}")
    print(f"Using created_date: {created_date}")
    
    # Create requirements_checklist table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS requirements_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requirement VARCHAR(500) NOT NULL,
        rule TEXT NOT NULL,
        citations TEXT,
        hash VARCHAR(50) NOT NULL,
        created_date DATETIME NOT NULL
    )
    """
    
    cursor.execute(create_table_sql)
    print("Table 'requirements_checklist' created/verified")
    
    # Process each section and its rules
    records_inserted = 0
    
    for section in data.get('sections', []):
        section_title = section.get('title', '')
        
        # Process rules in the main section
        for rule in section.get('rules', []):
            rule_text = rule.get('text', '')
            rule_id = rule.get('id', '')
            citations = rule.get('citations', [])
            
            # Extract citation hrefs and join with commas
            citation_links = [c.get('href', '') for c in citations if c.get('href')]
            citations_str = ', '.join(citation_links) if citation_links else None
            
            # Insert record
            insert_sql = """
            INSERT INTO requirements_checklist (requirement, rule, citations, hash, created_date) 
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(insert_sql, (section_title, rule_text, citations_str, rule_id, created_date))
            records_inserted += 1
        
        # Process rules in subsections
        for subsection in section.get('subsections', []):
            for rule in subsection.get('rules', []):
                rule_text = rule.get('text', '')
                rule_id = rule.get('id', '')
                citations = rule.get('citations', [])
                
                # Extract citation hrefs and join with commas
                citation_links = [c.get('href', '') for c in citations if c.get('href')]
                citations_str = ', '.join(citation_links) if citation_links else None
                
                # Insert record
                insert_sql = """
                INSERT INTO requirements_checklist (requirement, rule, citations, hash, created_date) 
                VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(insert_sql, (section_title, rule_text, citations_str, rule_id, created_date))
                records_inserted += 1
    
    # Commit changes
    conn.commit()
    
    print(f"Inserted {records_inserted} records into 'requirements_checklist' table")
    
    # Display summary
    print(f"\n{'='*60}")
    print("UPDATED DATABASE SUMMARY")
    print(f"{'='*60}")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Table: {table_name} - Records: {count}")
    
    # Show sample records from requirements_checklist
    print(f"\n{'='*60}")
    print("SAMPLE REQUIREMENTS_CHECKLIST RECORDS")
    print(f"{'='*60}")
    
    cursor.execute("""
    SELECT id, requirement, rule, citations, hash 
    FROM requirements_checklist 
    LIMIT 5
    """)
    
    sample_records = cursor.fetchall()
    for record in sample_records:
        print(f"ID: {record[0]}")
        print(f"Requirement: {record[1]}")
        print(f"Rule: {record[2][:80]}...")
        print(f"Citations: {record[3][:80] + '...' if record[3] and len(record[3]) > 80 else record[3]}")
        print(f"Hash: {record[4]}")
        print("-" * 40)
    
    conn.close()
    print(f"\nDatabase updated successfully!")

def view_requirements_checklist_stats():
    """Optional: View statistics about the requirements_checklist table"""
    db_file = Path(__file__).parent.parent.parent / "data" / "ilt_requirements.db"
    
    if not db_file.exists():
        print("Database not found.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Count by requirement (section)
    print("\nRequirements by Section:")
    cursor.execute("""
    SELECT requirement, COUNT(*) as rule_count 
    FROM requirements_checklist 
    GROUP BY requirement 
    ORDER BY rule_count DESC
    """)
    
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} rules")
    
    # Count rules with citations
    cursor.execute("""
    SELECT 
        COUNT(*) as total_rules,
        COUNT(CASE WHEN citations IS NOT NULL THEN 1 END) as rules_with_citations,
        COUNT(CASE WHEN citations IS NULL THEN 1 END) as rules_without_citations
    FROM requirements_checklist
    """)
    
    stats = cursor.fetchone()
    print(f"\nCitation Statistics:")
    print(f"  Total rules: {stats[0]}")
    print(f"  Rules with citations: {stats[1]}")
    print(f"  Rules without citations: {stats[2]}")
    
    conn.close()

if __name__ == "__main__":
    create_requirements_checklist_table()
    print("\n" + "="*60)
    print("Want to view statistics? Uncomment the line below:")
    print("# view_requirements_checklist_stats()")
    # view_requirements_checklist_stats()