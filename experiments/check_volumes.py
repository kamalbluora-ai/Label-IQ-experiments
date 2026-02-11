import sqlite3

conn = sqlite3.connect('ilt_requirements.db')
cursor = conn.cursor()

# Check all volumes
cursor.execute('SELECT DISTINCT volume FROM cfcs_cname ORDER BY volume')
all_volumes = cursor.fetchall()

print("ALL VOLUMES CURRENTLY IN DATABASE:")
for i, (vol,) in enumerate(all_volumes, 1):
    cursor.execute('SELECT COUNT(*) FROM cfcs_cname WHERE volume = ?', (vol,))
    count = cursor.fetchone()[0]
    print(f"{i:2d}. {vol}: {count} names")

print("\nVOLUME 11 VARIANTS:")
cursor.execute("SELECT DISTINCT volume FROM cfcs_cname WHERE volume LIKE '%Volume 11%' ORDER BY volume")
vol11_variants = cursor.fetchall()
for vol, in vol11_variants:
    cursor.execute('SELECT COUNT(*) FROM cfcs_cname WHERE volume = ?', (vol,))
    count = cursor.fetchone()[0]
    print(f"  {vol}: {count} names")

print("\nSEARCHING FOR 'PREPACKAGED WATER' CONTENT:")
cursor.execute("SELECT common_name, volume, tag FROM cfcs_cname WHERE common_name LIKE '%water%' OR definition LIKE '%water%' OR volume LIKE '%water%' LIMIT 10")
water_related = cursor.fetchall()
for name, vol, tag in water_related:
    print(f"  {name} | {vol} | {tag}")

conn.close()