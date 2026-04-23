from pathlib import Path
import os
import sqlite3
import urllib.request
import secrets
from fastapi import FastAPI, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

base_folder = Path(__file__).resolve().parent.parent
db_path = base_folder / "emails.db"
templates = Jinja2Templates(directory=str(base_folder / "templates"))

DB_URL = os.environ.get("DB_URL", "")
APP_USERNAME = os.environ.get("APP_USERNAME", "")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
APP_SESSION_SECRET = os.environ.get("APP_SESSION_SECRET", "")

if not db_path.exists() and DB_URL:
    print("Downloading database...")
    urllib.request.urlretrieve(DB_URL, db_path)
    print("Database downloaded.")

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
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()

def make_preview(body):
    return clean_text(body)[:250]

def get_expected_session_value():
    return f"{APP_USERNAME}:{APP_SESSION_SECRET}"

def is_logged_in(request: Request):
    session_cookie = request.cookies.get("aueco_session")
    return session_cookie == get_expected_session_value()

def require_login(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return None

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": ""}
    )

@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == APP_USERNAME and password == APP_PASSWORD:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="aueco_session",
            value=get_expected_session_value(),
            httponly=True,
            samesite="lax",
            secure=True
        )
        return response

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Incorrect username or password."},
        status_code=401
    )

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("aueco_session")
    return response

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.get("/search")
def search_emails(request: Request, q: str = Query(default="")):
    redirect = require_login(request)
    if redirect:
        return []

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
def get_email(request: Request, email_id: int):
    redirect = require_login(request)
    if redirect:
        return {"error": "Not authenticated"}

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