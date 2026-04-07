from pathlib import Path
import sqlite3
from datetime import datetime
import re
import html
import pypff

base_folder = Path(__file__).resolve().parent.parent
data_folder = base_folder / "data"
db_path = base_folder / "emails.db"

pst_files = [
    data_folder / "archive.pst",
    data_folder / "archive2.pst",
]

print("Creating DB:", db_path)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS emails")

cur.execute("""
CREATE TABLE emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pst_file TEXT,
    subject TEXT,
    sender TEXT,
    sent_at TEXT,
    body TEXT
)
""")

email_count = 0
error_count = 0

def normalize_date(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)

def decode_if_bytes(value):
    if not value:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore")
        except Exception:
            return value.decode("latin-1", errors="ignore")
    return str(value)

def html_to_text(value):
    text = decode_if_bytes(value)
    if not text:
        return ""

    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"(?i)</div\s*>", "\n", text)
    text = re.sub(r"(?i)</li\s*>", "\n", text)
    text = re.sub(r"(?s)<.*?>", " ", text)

    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()

def clean_text(text):
    text = decode_if_bytes(text)
    if not text:
        return ""

    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove common external warning banners
    text = text.replace(
        "WARNING: This message has originated from an External Source.", ""
    )
    text = text.replace(
        "This may be a phishing expedition that can result in unauthorized "
        "access to our IT System. Please use proper judgment and caution when "
        "opening attachments, clicking links, or responding to this email.",
        ""
    )

    text = text.replace("This Message Is From an External Sender", "")
    text = text.replace("This message came from outside your organization.", "")
    text = text.replace("ZjQcmQRYFpfptBannerStart", "")
    text = text.replace("ZjQcmQRYFpfptBannerEnd", "")

  # Normalize spaces before/after line breaks
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)

    # Collapse repeated spaces/tabs
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Collapse 3+ blank lines to just 1 blank line
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

def safe_get(attr_func):
    try:
        return attr_func()
    except Exception:
        return ""

def get_message_body(msg):
    plain = clean_text(safe_get(lambda: msg.plain_text_body))
    if plain:
        return plain

    html_body = clean_text(html_to_text(safe_get(lambda: msg.html_body)))
    if html_body:
        return html_body

    rtf_body = clean_text(safe_get(lambda: msg.rtf_body))
    if rtf_body:
        return rtf_body

    return ""

def walk(folder, pst_name):
    global email_count, error_count

    for i in range(folder.number_of_sub_messages):
        try:
            msg = folder.get_sub_message(i)

            subject = clean_text(safe_get(lambda: msg.subject))
            sender = clean_text(safe_get(lambda: msg.sender_name))
            body = get_message_body(msg)

            sent_raw = None
            try:
                if hasattr(msg, "client_submit_time"):
                    sent_raw = msg.client_submit_time
                elif hasattr(msg, "delivery_time"):
                    sent_raw = msg.delivery_time
            except Exception:
                sent_raw = None

            sent_at = normalize_date(sent_raw)

            cur.execute(
                "INSERT INTO emails (pst_file, subject, sender, sent_at, body) VALUES (?, ?, ?, ?, ?)",
                (pst_name, subject, sender, sent_at, body)
            )

            email_count += 1
            if email_count % 500 == 0:
                print(f"Processed {email_count} emails...")

        except Exception:
            error_count += 1
            print(f"Skipped one message in {pst_name}. Total skipped: {error_count}")
            continue

    for j in range(folder.number_of_sub_folders):
        try:
            walk(folder.get_sub_folder(j), pst_name)
        except Exception:
            error_count += 1
            print(f"Skipped one folder in {pst_name}. Total skipped: {error_count}")
            continue

for pst_path in pst_files:
    print("Processing PST:", pst_path)

    pst = pypff.file()
    pst.open(str(pst_path))

    root = pst.get_root_folder()
    walk(root, pst_path.name)

    pst.close()

conn.commit()
conn.close()

print(f"Done! Stored {email_count} emails in emails.db")
print(f"Skipped {error_count} problematic messages/folders")