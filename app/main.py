from pathlib import Path
import os
import sqlite3
import urllib.request
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

base_folder = Path(__file__).resolve().parent.parent
db_path = base_folder / "emails.db"
templates = Jinja2Templates(directory=str(base_folder / "templates"))

DB_URL = os.environ.get("DB_URL", "")

print("Starting app...")
print("DB path:", db_path)
print("DB_URL set:", bool(DB_URL))

if not db_path.exists():
    print("Downloading database...")
    urllib.request.urlretrieve(DB_URL, db_path)
    print("Database downloaded.")

print("DB exists:", db_path.exists())

# verify it looks like a real SQLite file
if db_path.exists():
    with open(db_path, "rb") as f:
        header = f.read(16)
    print("DB header:", header)

app = FastAPI()

def get_connection():
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"

@app.get("/dbcheck", response_class=PlainTextResponse)
def dbcheck():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM emails")
        count = cur.fetchone()[0]
        conn.close()
        return f"db ok, emails={count}"
    except Exception as e:
        return f"db error: {e}"

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