from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import uuid
from datetime import datetime, timedelta
from app.models import db_setup
import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# Load environment variables from a .env file (if present)
load_dotenv(find_dotenv(), override=True)  # CHANGED: ensure the correct .env is loaded

# Optional: set via env to change models without code changes
# e.g. OPENAI_MODEL=gpt-4o-mini
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()  # CHANGED: strip whitespace

_client: Optional[OpenAI] = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        # Uses OPENAI_API_KEY from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Raise a clear error so caller can handle gracefully
            raise RuntimeError("Missing OPENAI_API_KEY environment variable")
        # Optional org/project scoping if your key requires it
        org_id = os.getenv("OPENAI_ORG_ID")
        project_id = os.getenv("OPENAI_PROJECT_ID")
        kwargs = {}
        if org_id:
            kwargs["organization"] = org_id
        if project_id:
            kwargs["project"] = project_id
        _client = OpenAI(api_key=api_key, **kwargs)
    return _client

def get_ai_response(prompt: str) -> str:
    """
    Get an assistant reply using OpenAI's Chat Completions API.
    Requires OPENAI_API_KEY to be set in your environment.
    """
    try:
        client = _get_client()
        # Use Chat Completions for broad compatibility
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI character."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        content = resp.choices[0].message.content if resp.choices and resp.choices[0].message else ""
        return (content or "").strip()
    except Exception as e:
        msg = str(e)
        name = e.__class__.__name__
        if name == "RuntimeError" and "OPENAI_API_KEY" in msg:
            return "Sorry, I couldn't get a response right now. (Missing OPENAI_API_KEY)"
        if "Authentication" in name:
            return "Sorry, I couldn't get a response right now. (AuthenticationError: verify OPENAI_API_KEY; if needed set OPENAI_ORG_ID/OPENAI_PROJECT_ID; confirm model access)"
        if "BadRequest" in name or "NotFound" in name:
            return "Sorry, I couldn't get a response right now. (BadRequestError: check OPENAI_MODEL name and access)"
        return f"Sorry, I couldn't get a response right now. ({name})"

# Explicitly set template/static folders so Flask always finds them
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"  # 🔑 change for production
db_setup.init_db()

# Quick health check route to confirm routing works
@app.route("/health")
def health():
    return "OK", 200

# Optional: serve favicon to avoid 404s in logs
@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")

# ----------------------
# AUTH: LOGOUT
# ----------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ----------------------
# LOGIN (very basic demo)
# ----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(db_setup.DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect(url_for("home"))
        else:
            return "Invalid login. Try again."

    return render_template("login.html")

# ----------------------
# HOME / CHAT
# ----------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # load characters for dropdown
    conn = sqlite3.connect(db_setup.DB_PATH)
    c = conn.cursor()
    # Deduplicate by name: keep the lowest id per name
    c.execute("""
        SELECT MIN(id) AS id, name
        FROM characters
        GROUP BY name
        ORDER BY name COLLATE NOCASE
    """)
    characters = c.fetchall()
    conn.close()

    selected_character = None
    ai_reply = None
    user_message = None
    conversation = []

    if request.method == "POST":
        # Character may be posted from either the switcher or the composer form
        char_raw = request.form.get("character")
        if char_raw is not None:
            char_raw = char_raw.strip()
            if char_raw:
                try:
                    selected_character = int(char_raw)
                except ValueError:
                    selected_character = None  # ignore bad input

        # Only send to AI when a non-empty message is provided
        if "message" in request.form:
            user_message = (request.form.get("message") or "").strip()
            if user_message and selected_character is not None:
                # fetch character persona
                conn = sqlite3.connect(db_setup.DB_PATH)
                c = conn.cursor()
                c.execute("SELECT persona_prompt FROM characters WHERE id=?", (selected_character,))
                persona_row = c.fetchone()
                conn.close()

                persona = persona_row[0] if persona_row else "You are a helpful assistant."

                # build prompt
                prompt = f"{persona}\nUser: {user_message}"
                ai_reply = get_ai_response(prompt)

                # save both messages
                conn = sqlite3.connect(db_setup.DB_PATH)
                c = conn.cursor()
                c.execute(
                    "INSERT INTO conversations (user_id, character_id, message, role) VALUES (?, ?, ?, ?)",
                    (user_id, selected_character, user_message, "user"),
                )
                c.execute(
                    "INSERT INTO conversations (user_id, character_id, message, role) VALUES (?, ?, ?, ?)",
                    (user_id, selected_character, ai_reply, "ai"),
                )
                conn.commit()
                conn.close()

    # always fetch conversation if a character is selected
    if selected_character:
        conversation = fetch_history(user_id, selected_character)

    return render_template(
        "index.html",
        characters=characters,
        selected_character=selected_character,
        conversation=conversation,
        ai_reply=ai_reply,
        user_message=user_message
    )

# static/enter-submit.js
@app.route("/static/enter-submit.js")
def enter_submit_js():
    return app.send_static_file("enter-submit.js")

# Add this small alias so /index works too
@app.route("/index")
def index_alias():
    return redirect(url_for("home"))

if __name__ == "__main__":
    # Bind explicitly to IPv4 localhost and a fixed port; disable reloader for a single clean process
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)

# function to fetch conversation history
from app.models.db_setup import DB_PATH

def get_history(user_id, character_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT role, message FROM conversations WHERE user_id=? AND character_id=? ORDER BY timestamp ASC",
        (user_id, character_id)
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "message": r[1]} for r in rows]

# added user connection and reverse
from flask import Flask, jsonify

app = Flask(__name__)
DB_NAME = "characters.db"

# --- DB setup ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS character_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER NOT NULL,
        linked_character_id INTEGER NOT NULL,
        relationship_type TEXT,
        FOREIGN KEY(character_id) REFERENCES characters(id),
        FOREIGN KEY(linked_character_id) REFERENCES characters(id),
        UNIQUE(character_id, linked_character_id) -- 🚀 prevents duplicates
    )
    """)
    conn.commit()
    conn.close()

init_db()

# --- API routes ---

@app.route("/characters", methods=["POST"])
def create_character():
    data = request.json
    user_id = data.get("user_id")
    name = data.get("name")
    description = data.get("description", "")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO characters (user_id, name, description) VALUES (?, ?, ?)",
                   (user_id, name, description))
    conn.commit()
    char_id = cursor.lastrowid
    conn.close()

    return jsonify({"id": char_id, "user_id": user_id, "name": name, "description": description}), 201


@app.route("/characters/<int:char_id>/connect", methods=["POST"])
def connect_characters(char_id):
    data = request.json
    other_char_id = data.get("other_char_id")
    relationship = data.get("relationship", "linked")

    if char_id == other_char_id:
        return jsonify({"error": "A character cannot connect to itself"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # Insert forward connection if not exists
        cursor.execute("""INSERT OR IGNORE INTO character_links (character_id, linked_character_id, relationship_type)
                          VALUES (?, ?, ?)""", (char_id, other_char_id, relationship))

        # Insert reverse connection if not exists
        cursor.execute("""INSERT OR IGNORE INTO character_links (character_id, linked_character_id, relationship_type)
                          VALUES (?, ?, ?)""", (other_char_id, char_id, relationship))

        conn.commit()
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()

    return jsonify({"message": f"Character {char_id} connected with {other_char_id} as {relationship} (both ways)"}), 201


@app.route("/characters/<int:char_id>/connections", methods=["GET"])
def get_connections(char_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.name, cl.relationship_type
        FROM character_links cl
        JOIN characters c ON cl.linked_character_id = c.id
        WHERE cl.character_id = ?
    """, (char_id,))
    rows = cursor.fetchall()
    conn.close()

    connections = [{"id": r[0], "name": r[1], "relationship": r[2]} for r in rows]
    return jsonify(connections)


if __name__ == "__main__":
    app.run(debug=True)

# add login
# ... existing code ...
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(db_setup.DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect(url_for("home"))
        else:
            return "Invalid login. Try again."

    return render_template("login.html")

# add this too?
# ... existing code ...
from flask import render_template, request, redirect, url_for, session, flash
import sqlite3
import uuid
from datetime import datetime, timedelta
from app.models import db_setup
# ... existing code ...

def _ensure_password_reset_schema():
    conn = sqlite3.connect(db_setup.DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        conn = sqlite3.connect(db_setup.DB_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        # Auto-login after successful registration
        c.execute("SELECT id FROM users WHERE email=?", (email,))
        row = c.fetchone()
        conn.close()
        if row:
            session["user_id"] = row[0]
            flash("Account created. You are now signed in.", "success")
            return redirect(url_for("home"))
        flash("Registration succeeded but login failed. Please sign in.", "warning")
        return redirect(url_for("login"))

    return render_template("register.html")

# Logout
@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))

# Forgot password: request reset link
@app.route("/password/forgot", methods=["GET", "POST"])
def forgot_password():
    _ensure_password_reset_schema()
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            flash("Please enter your email.", "error")
            return render_template("reset_request.html")

        # Verify user exists (do not reveal which addresses are registered)
        conn = sqlite3.connect(db_setup.DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=?", (email,))
        user = c.fetchone()

        # Always create a token (or pretend to) to avoid leaking user existence
        token = str(uuid.uuid4())
        expires_at = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        if user:
            try:
                c.execute(
                    "INSERT INTO password_resets (email, token, expires_at) VALUES (?, ?, ?)",
                    (email, token, expires_at),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                # Rare token collision; try once more
                token = str(uuid.uuid4())
                c.execute(
                    "INSERT INTO password_resets (email, token, expires_at) VALUES (?, ?, ?)",
                    (email, token, expires_at),
                )
                conn.commit()
        conn.close()

        # In a real app you would email this link. For now we display it.
        reset_url = url_for("reset_password", token=token, _external=True)
        return render_template("reset_request.html", reset_url=reset_url, email=email)

    return render_template("reset_request.html")

# Password reset: set new password using token
@app.route("/password/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    _ensure_password_reset_schema()
    conn = sqlite3.connect(db_setup.DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT email, expires_at FROM password_resets WHERE token=?",
        (token,),
    )
    row = c.fetchone()

    if not row:
        conn.close()
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("forgot_password"))

    email, expires_at_str = row
    try:
        expires_at = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        expires_at = datetime.utcnow() - timedelta(seconds=1)

    if datetime.utcnow() > expires_at:
        # Expired: clean up token
        c.execute("DELETE FROM password_resets WHERE token=?", (token,))
        conn.commit()
        conn.close()
        flash("Reset link has expired. Please request a new one.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        if not password:
            flash("Please enter a new password.", "error")
            conn.close()
            return render_template("reset_password.html", token=token, email=email)
        if password != confirm:
            flash("Passwords do not match.", "error")
            conn.close()
            return render_template("reset_password.html", token=token, email=email)

        # Update password and invalidate token
        c.execute("UPDATE users SET password=? WHERE email=?", (password, email))
        c.execute("DELETE FROM password_resets WHERE token=?", (token,))
        conn.commit()
        conn.close()
        flash("Your password has been updated. Please sign in.", "success")
        return redirect(url_for("login"))

    conn.close()
    return render_template("reset_password.html", token=token, email=email)


# add tiktok app
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

app = FastAPI()
# Use existing root-level static/templates instead of app/static and app/templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    videos = os.listdir(UPLOAD_DIR)
    return templates.TemplateResponse("index.html", {"request": request, "videos": videos})

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    with open(os.path.join(UPLOAD_DIR, file.filename), "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse("/", status_code=302)


# add session middleware
# app/main.py
# from app.route import user_routes, video_routes  # REMOVE: these modules don't exist
from starlette.middleware.sessions import SessionMiddleware
import os

# Reuse the existing FastAPI app created earlier; DO NOT re-create or remount here
# app = FastAPI()  # REMOVE duplicate app creation
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")  # Same as in auth.py

# app.mount("/static", StaticFiles(directory="app/static"), name="static")  # REMOVE: wrong path & duplicate
# templates = Jinja2Templates(directory="app/templates")  # REMOVE: duplicate

# app.include_router(user_routes.router)  # REMOVE: module doesn't exist
# app.include_router(video_routes.router)  # REMOVE: module doesn't exist

# Ensure upload dir exists (aligned with the first mount at "static")
os.makedirs("static/uploads", exist_ok=True)

# User Feed + Upload Video System
# register the router
# from app.routes import video_routes  # REMOVE: module path invalid
# app.include_router(video_routes.router)  # REMOVE

# homepage route
# from fastapi import Request  # already imported above
# from app.main import templates  # REMOVE circular import & duplicate templates

# @app.get("/")
# def home(request: Request):
#     return templates.TemplateResponse("home.html", {"request": request})

# add explorer route
from app.routes.feed_router import router as feed_router
# Include the APIRouter object directly
app.include_router(feed_router)

# Register router
# from app.routes.user_router import router as user_router  # REMOVE if this module doesn't exist
# app.include_router(user_router)

# Profile Editing Form
import shutil
from fastapi import Form, UploadFile, File
from fastapi.responses import RedirectResponse
from app.models import User
from fastapi import status

@router.get("/edit-profile")
def edit_profile_get(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()  # 🔒 Replace with current_user when auth is ready
    return templates.TemplateResponse("edit_profile.html", {
        "request": request,
        "user": user
    })

@router.post("/edit-profile")
def edit_profile_post(
    request: Request,
    username: str = Form(...),
    bio: str = Form(...),
    profile_pic: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = db.query(User).first()  # 🔒 Replace with current_user

    user.username = username
    user.bio = bio

    # ✅ Save uploaded profile picture
    if profile_pic:
        file_ext = profile_pic.filename.split(".")[-1]
        file_name = f"profile_{user.id}.{file_ext}"
        file_path = f"static/uploads/{file_name}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(profile_pic.file, buffer)

        user.profile_pic = f"/static/uploads/{file_name}"

    db.commit()
    return RedirectResponse(f"/user/{user.id}", status_code=status.HTTP_302_FOUND)

