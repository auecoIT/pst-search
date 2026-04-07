from pathlib import Path
import sqlite3

base_folder = Path(__file__).resolve().parent.parent
db_path = base_folder / "emails.db"

def make_preview(body):
    if not body:
        return ""

    warning_phrase = "WARNING: This message has originated from an External Source."

    if warning_phrase in body:
        body = body.replace(warning_phrase, "").strip()

        extra_phrase = (
            "This may be a phishing expedition that can result in unauthorized "
            "access to our IT System. Please use proper judgment and caution when "
            "opening attachments, clicking links, or responding to this email."
        )
        body = body.replace(extra_phrase, "").strip()

    return body[:200]

search_term = input("Enter a keyword to search for: ").strip()

conn = sqlite3.connect(db_path)
cur = conn.cursor()

query = """
SELECT id, pst_file, subject, sender, body
FROM emails
WHERE subject LIKE ? OR sender LIKE ? OR body LIKE ?
LIMIT 20
"""

like_term = f"%{search_term}%"
cur.execute(query, (like_term, like_term, like_term))
rows = cur.fetchall()

print()
print(f"Found {len(rows)} matching emails")
print()

for row in rows:
    email_id, pst_file, subject, sender, body = row
    print("-----")
    print("ID:", email_id)
    print("PST:", pst_file)
    print("Subject:", subject)
    print("Sender:", sender)
    print("Body preview:", make_preview(body))

conn.close()