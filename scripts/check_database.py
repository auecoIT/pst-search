from pathlib import Path
import sqlite3

base_folder = Path(__file__).resolve().parent.parent
db_path = base_folder / "emails.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM emails")
count = cur.fetchone()[0]
print("Total emails:", count)

cur.execute("SELECT COUNT(*) FROM emails_fts")
fts_count = cur.fetchone()[0]
print("Total indexed in FTS:", fts_count)

cur.execute("""
SELECT e.id, e.subject, e.sender, e.sent_at
FROM emails_fts f
JOIN emails e ON e.id = f.rowid
WHERE emails_fts MATCH 'Cuba'
LIMIT 5
""")
rows = cur.fetchall()

print("Sample FTS search results for 'Cuba':")
for row in rows:
    print(row)

conn.close()