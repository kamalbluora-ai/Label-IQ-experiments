import sqlite3

conn = sqlite3.connect('ilt_requirements.db')
cursor = conn.cursor()

print("VOLUME 11 - PREPACKAGED WATER CONTENT:")
cursor.execute("SELECT common_name, volume, tag FROM cfcs_cname WHERE volume LIKE '%Prepackaged Water%' ORDER BY common_name")
water_rows = cursor.fetchall()

for name, vol, tag in water_rows:
    print(f"  {name} | {vol} | {tag}")

print(f"\nFound {len(water_rows)} prepackaged water items")

# Check all Volume 11 variants now
print("\nALL VOLUME 11 VARIANTS:")
cursor.execute("SELECT DISTINCT volume FROM cfcs_cname WHERE volume LIKE '%Volume 11%' ORDER BY volume")
vol11_variants = cursor.fetchall()

for vol, in vol11_variants:
    cursor.execute('SELECT COUNT(*) FROM cfcs_cname WHERE volume = ?', (vol,))
    count = cursor.fetchone()[0]
    print(f"  {vol}: {count} names")

# Total count
cursor.execute('SELECT COUNT(*) FROM cfcs_cname')
total = cursor.fetchone()[0]
print(f"\nTotal records in database: {total}")

conn.close()