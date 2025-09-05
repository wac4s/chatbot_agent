import sqlite3
import os

# Resolve the database path to the project root: <project_root>/chat.db
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chat.db"))

def _ensure_users_schema(c):
    # Create `users` table if it doesn't exist with the desired schema (email-based)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Check current columns for possible legacy schema (with `username` but no `email`)
    cols = [row[1] for row in c.execute("PRAGMA table_info(users)")]  # row[1] is column name
    has_email = 'email' in cols
    has_username = 'username' in cols

    if not has_email and has_username:
        # Migrate: add email column (SQLite cannot add UNIQUE via ALTER TABLE)
        c.execute("ALTER TABLE users ADD COLUMN email TEXT")
        # Backfill where email is missing
        c.execute("""
            UPDATE users
            SET email = username
            WHERE (email IS NULL OR email = '')
              AND username IS NOT NULL
              AND username <> ''
        """)
        # Try to enforce uniqueness with a unique index
        try:
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        except sqlite3.OperationalError as e:
            print("Warning: Could not create unique index on users.email. Reason:", str(e))
            print("Resolve duplicate or null emails in `users` and re-run this script.")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Ensure users table and migrate if needed
    _ensure_users_schema(c)

    # Characters table
    c.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            persona_prompt TEXT
        )
    ''')

    # Conversations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            character_id INTEGER,
            message TEXT,
            role TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(character_id) REFERENCES characters(id)
        )
    ''')

    # Seed test user (idempotent)
    c.execute("INSERT OR IGNORE INTO users (email, password) VALUES (?, ?)",
              ("testuser@example.com", "password123"))

    # Seed characters
    characters = [
        ("Alice", "You are Alice, a cheerful and supportive AI friend."),
        ("Professor Bot", "You are a knowledgeable professor who explains things clearly."),
        ("Sassy Cat", "You are a sarcastic, witty cat who talks like a human.")
    ]
    for name, prompt in characters:
        try:
            c.execute("INSERT INTO characters (name, persona_prompt) VALUES (?, ?)", (name, prompt))
        except sqlite3.IntegrityError:
            pass  # character already exists

    conn.commit()
    conn.close()
    print(f"Database initialized and seeded successfully at: {DB_PATH}")

def _ensure_password_reset_schema():
    conn = sqlite3.connect(DB_PATH)
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

        conn = sqlite3.connect(DB_PATH)
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

def logout():
    session.pop("user_id", None)
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))

# Forgot password: request reset link

def forgot_password():
    _ensure_password_reset_schema()
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            flash("Please enter your email.", "error")
            return render_template("reset_request.html")

        # Verify user exists (do not reveal which addresses are registered)
        conn = sqlite3.connect(DB_PATH)
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

def reset_password(token):
    _ensure_password_reset_schema()
    conn = sqlite3.connect(DB_PATH)
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

if __name__ == "__main__":
    init_db()

# Stores users, messages, servers, and channels
# something about schemas change from here.
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "super secret key"  # Change this in production!