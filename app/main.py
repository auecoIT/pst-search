from pathlib import Path
import sqlite3
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

base_folder = Path(__file__).resolve().parent.parent
db_path = base_folder / "emails.db"
templates = Jinja2Templates(directory=str(base_folder / "templates"))

app = FastAPI()

def get_connection():
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def clean_text(text):
    if not text:
        return ""

    warning_phrase = "WARNING: This message has originated from an External Source."
    extra_phrase = (
        "This may be a phishing expedition that can result in unauthorized "
        "access to our IT System. Please use proper judgment and caution when "
        "opening attachments, clicking links, or responding to this email."
    )

    text = text.replace(warning_phrase, "")
    text = text.replace(extra_phrase, "")

    # Remove null characters and normalize line endings
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    return text.strip()

def make_preview(body):
    return clean_text(body)[:250]

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.get("/search")
def search_emails(q: str = Query(default="")):
    if not q.strip():
        return []

    conn = get_connection()
    cur = conn.cursor()

    like_term = "%" + q + "%"
    cur.execute(
        """
        SELECT id, pst_file, subject, sender, sent_at, body
        FROM emails
        WHERE subject LIKE ? OR sender LIKE ? OR body LIKE ?
        ORDER BY sent_at DESC
        LIMIT 50
        """,
        (like_term, like_term, like_term),
    )

    rows = cur.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "pst_file": row["pst_file"] or "",
            "subject": row["subject"] or "(no subject)",
            "sender": row["sender"] or "(unknown sender)",
            "sent_at": row["sent_at"] or "",
            "preview": make_preview(row["body"] or ""),
        })

    return results

@app.get("/email/{email_id}")
def get_email(email_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, pst_file, subject, sender, sent_at, body
        FROM emails
        WHERE id = ?
        """,
        (email_id,),
    )

    row = cur.fetchone()
    conn.close()

    if row is None:
        return {"error": "Not found"}

    return {
        "id": row["id"],
        "pst_file": row["pst_file"] or "",
        "subject": clean_text(row["subject"] or "(no subject)"),
        "sender": clean_text(row["sender"] or "(unknown sender)"),
        "sent_at": row["sent_at"] or "",
        "body": clean_text(row["body"] or ""),
    }