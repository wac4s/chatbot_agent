# function to fetch conversation history
import sqlite3
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



def get_history(user_id, character_id):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute(
        "SELECT role, message FROM conversations WHERE user_id=? AND character_id=? ORDER BY timestamp ASC",
        (user_id, character_id)
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "message": r[1]} for r in rows]
