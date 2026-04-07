from pathlib import Path
import sqlite3

base_folder = Path(__file__).resolve().parent.parent
db_path = base_folder / "emails.db"

email_id = input("Enter the email ID to view: ").strip()

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
SELECT id, subject, sender, body
FROM emails
WHERE id = ?
""", (email_id,))

row = cur.fetchone()

if row is None:
    print("No email found with that ID.")
else:
    email_id, subject, sender, body = row
    print()
    print("ID:", email_id)
    print("Subject:", subject)
    print("Sender:", sender)
    print()
    print("BODY:")
    print(body)

conn.close()