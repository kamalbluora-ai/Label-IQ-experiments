import json
import sqlite3
import re
from datetime import datetime
from pathlib import Path

def sanitize_table_name(name):
    """Convert section title to valid SQL table name"""
    # Convert to lowercase and replace spaces/special chars with underscores
    table_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
    # Remove multiple underscores and leading/trailing underscores
    table_name = re.sub(r'_+', '_', table_name).strip('_')
    return table_name

def create_database_from_ilt():
    """Create SQLite database with tables for each section"""
    
    # Paths
    json_file = Path("ILT/industry_labelling_tool.json")
    db_file = Path(__file__).parent.parent / "data" / "ilt_requirements.db"
    
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
    
    # Connect to SQLite database (creates if not exists)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"Creating database: {db_file}")
    print(f"Using created_date: {created_date}")
    
    # Reset all sequences at the start for a clean state
    print("Resetting all auto-increment sequences...")
    cursor.execute("DELETE FROM sqlite_sequence")
    conn.commit()
    
    # Process each section
    for section in data.get('sections', []):
        section_title = section.get('title', '')
        table_name = sanitize_table_name(section_title)
        
        print(f"\nProcessing section: {section_title}")
        print(f"Table name: {table_name}")
        
        # Create table if not exists with citations column
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requirement VARCHAR(500) NOT NULL,
            citations TEXT,
            created_date DATETIME NOT NULL
        )
        """
        
        cursor.execute(create_table_sql)
        
        # Check if citations column exists, if not add it
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'citations' not in columns:
            print(f"Adding citations column to {table_name}")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN citations TEXT")
        
        print(f"Table '{table_name}' created/verified with citations column")
        
        # Clear existing data to avoid duplicates on re-run
        cursor.execute(f"DELETE FROM {table_name}")
        
        # Reset the auto-increment sequence for this table
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
        conn.commit()
        print(f"Reset sequence for table '{table_name}'")
        
        # Insert citations as requirements
        citations = section.get('citations', [])
        for citation in citations:
            requirement_text = citation.get('text', '')
            citation_href = citation.get('href', '')
            
            if requirement_text:
                insert_sql = f"""
                INSERT INTO {table_name} (requirement, citations, created_date) 
                VALUES (?, ?, ?)
                """
                cursor.execute(insert_sql, (requirement_text, citation_href, created_date))
        
        print(f"Inserted {len(citations)} requirements into '{table_name}'")
    
    # Commit changes and close
    conn.commit()
    
    # Display summary
    print(f"\n{'='*60}")
    print("DATABASE SUMMARY")
    print(f"{'='*60}")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Table: {table_name} - Records: {count}")
    
    # Show sample records with citations
    print(f"\n{'='*60}")
    print("SAMPLE RECORDS WITH CITATIONS")
    print(f"{'='*60}")
    
    for (table_name,) in tables:
        # Only show our requirements tables (skip system tables like sqlite_sequence)
        if table_name in ['core_labelling_requirements', 'claims_and_statements', 'food_specific_labelling_requirements']:
            print(f"\n--- Table: {table_name} ---")
            cursor.execute(f"SELECT id, requirement, citations FROM {table_name} LIMIT 3")
            rows = cursor.fetchall()
            
            for row in rows:
                print(f"ID: {row[0]}")
                print(f"Requirement: {row[1]}")
                print(f"Citation URL: {row[2]}")
                print("-" * 30)
    
    conn.close()
    print(f"\nDatabase created successfully: {db_file}")
    print(f"Location: {db_file.absolute()}")

def view_database_content():
    """Optional: View the content of created database"""
    db_file = Path(__file__).parent.parent / "data" / "ilt_requirements.db"
    
    if not db_file.exists():
        print("Database not found. Run create_database_from_ilt() first.")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        print(f"\n--- Table: {table_name} ---")
        cursor.execute(f"SELECT id, requirement, citations, created_date FROM {table_name} LIMIT 5")
        rows = cursor.fetchall()
        
        for row in rows:
            print(f"ID: {row[0]}")
            print(f"Requirement: {row[1][:50]}...")
            print(f"Citation: {row[2][:60]}..." if row[2] and len(row[2]) > 60 else f"Citation: {row[2]}")
            print(f"Created: {row[3]}")
            print("-" * 40)
        
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total = cursor.fetchone()[0]
        if total > 5:
            print(f"... and {total - 5} more records")
    
    conn.close()

if __name__ == "__main__":
    create_database_from_ilt()
    print("\n" + "="*60)
    print("Want to view content? Uncomment the line below:")
    print("# view_database_content()")
    # view_database_content()