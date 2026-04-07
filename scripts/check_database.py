from pathlib import Path
import sqlite3

base_folder = Path(__file__).resolve().parent.parent
db_path = base_folder / "emails.db"

print("Opening database:", db_path)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM emails")
count = cur.fetchone()[0]
print("Total emails in database:", count)

cur.execute("""
SELECT id, pst_file, subject, sender, sent_at, body
FROM emails
ORDER BY sent_at DESC
LIMIT 5
""")
rows = cur.fetchall()

for row in rows:
    email_id, pst_file, subject, sender, sent_at, body = row
    print("-----")
    print("ID:", email_id)
    print("PST File:", pst_file)
    print("Date:", sent_at)
    print("Subject:", subject)
    print("Sender:", sender)
    print("Body preview:", body[:150])

conn.close()