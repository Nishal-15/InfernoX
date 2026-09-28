import sqlite3

conn = sqlite3.connect('thermal.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cursor.fetchall()]
print(f"Total tables: {len(tables)}")
for t in sorted(tables):
    if not t.startswith('sqlite') and not t.startswith('idx_') and not t.startswith('SpatialIndex') and not t.startswith('ElementaryGeometries'):
        try:
            cnt = cursor.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
            print(f"  {t}: {cnt}")
        except Exception as e:
            print(f"  {t}: error {e}")
