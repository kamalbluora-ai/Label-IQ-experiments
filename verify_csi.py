import sqlite3
from pathlib import Path

def verify_csi_extraction():
    """Verify the CSI extraction results"""
    
    db_file = Path("ilt_requirements.db")
    
    if not db_file.exists():
        print("Database not found!")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='csiv_cname'")
    if not cursor.fetchone():
        print("Table 'csiv_cname' does not exist. Run the extraction first.")
        conn.close()
        return
    
    print("CANADIAN STANDARDS OF IDENTITY EXTRACTION VERIFICATION")
    print("="*60)
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM csiv_cname")
    total_records = cursor.fetchone()[0]
    print(f"Total CSI Common Names: {total_records}")
    
    # Volume coverage
    cursor.execute("""
        SELECT volume_number, volume_title, COUNT(*) as count 
        FROM csiv_cname 
        WHERE volume_number IS NOT NULL
        GROUP BY volume_number, volume_title
        ORDER BY volume_number
    """)
    volume_results = cursor.fetchall()
    
    print(f"\nVolume Coverage ({len(volume_results)}/8 volumes):")
    expected_volumes = set(range(1, 9))
    covered_volumes = set()
    
    for vol_num, vol_title, count in volume_results:
        status = "✅" if count > 0 else "❌"
        print(f"  {status} Volume {vol_num} - {vol_title}: {count} names")
        covered_volumes.add(vol_num)
    
    missing_volumes = expected_volumes - covered_volumes
    if missing_volumes:
        print(f"\n❌ Missing Volumes: {sorted(missing_volumes)}")
    else:
        print(f"\n✅ All 8 volumes successfully extracted!")
    
    # Top sections
    cursor.execute("""
        SELECT section, COUNT(*) as count, volume_number
        FROM csiv_cname 
        WHERE section IS NOT NULL AND section != ''
        GROUP BY section, volume_number
        ORDER BY count DESC 
        LIMIT 10
    """)
    top_sections = cursor.fetchall()
    
    print(f"\nTop 10 Sections by Item Count:")
    for section, count, vol_num in top_sections:
        print(f"  Volume {vol_num}, Section {section}: {count} names")
    
    # Sample records from each volume
    print(f"\nSample Records by Volume:")
    for vol_num in sorted(covered_volumes):
        cursor.execute("""
            SELECT common_name, section, SUBSTR(definition, 1, 50) as def_preview
            FROM csiv_cname 
            WHERE volume_number = ?
            ORDER BY id
            LIMIT 3
        """, (vol_num,))
        
        samples = cursor.fetchall()
        print(f"\n  Volume {vol_num} samples:")
        for name, section, def_preview in samples:
            print(f"    {name} ({section}): {def_preview}...")
    
    # Search capabilities demonstration
    print(f"\nSearch Examples:")
    
    # Search for dairy products
    cursor.execute("SELECT common_name, volume_number FROM csiv_cname WHERE common_name LIKE '%milk%' OR common_name LIKE '%cheese%' OR common_name LIKE '%butter%' LIMIT 5")
    dairy_items = cursor.fetchall()
    if dairy_items:
        print(f"  Dairy products found: {len(dairy_items)} items")
        for name, vol in dairy_items[:3]:
            print(f"    {name} (Volume {vol})")
    
    # Search for meat products
    cursor.execute("SELECT common_name, volume_number FROM csiv_cname WHERE common_name LIKE '%meat%' OR common_name LIKE '%beef%' OR common_name LIKE '%pork%' LIMIT 5")
    meat_items = cursor.fetchall()
    if meat_items:
        print(f"  Meat products found: {len(meat_items)} items")
        for name, vol in meat_items[:3]:
            print(f"    {name} (Volume {vol})")
    
    # Quality metrics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN definition IS NOT NULL AND definition != '' THEN 1 END) as with_def,
            COUNT(CASE WHEN section IS NOT NULL AND section != '' THEN 1 END) as with_section,
            AVG(LENGTH(common_name)) as avg_name_length
        FROM csiv_cname
    """)
    
    total, with_def, with_section, avg_name_len = cursor.fetchone()
    
    print(f"\nData Quality Metrics:")
    print(f"  Total records: {total}")
    print(f"  Records with definitions: {with_def} ({with_def/total*100:.1f}%)")
    print(f"  Records with sections: {with_section} ({with_section/total*100:.1f}%)")
    print(f"  Average name length: {avg_name_len:.1f} characters")
    
    # Final status
    completeness_score = len(covered_volumes) / 8 * 100
    quality_score = (with_def / total) * 100 if total > 0 else 0
    
    print(f"\nExtraction Summary:")
    print(f"  Completeness: {completeness_score:.1f}% ({len(covered_volumes)}/8 volumes)")
    print(f"  Quality: {quality_score:.1f}% (records with definitions)")
    
    if completeness_score >= 87.5:  # 7/8 volumes
        print(f"  Status: ✅ EXCELLENT - Nearly complete extraction")
    elif completeness_score >= 62.5:  # 5/8 volumes
        print(f"  Status: ✅ GOOD - Majority of volumes extracted")
    elif completeness_score >= 37.5:  # 3/8 volumes  
        print(f"  Status: ⚠️ PARTIAL - Some volumes missing")
    else:
        print(f"  Status: ❌ INCOMPLETE - Many volumes missing")
    
    conn.close()

if __name__ == "__main__":
    verify_csi_extraction()