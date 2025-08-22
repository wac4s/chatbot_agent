import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

# Load env vars
load_dotenv()

# IMPORTANT:
# LangChain's ChatGoogleGenerativeAI expects GOOGLE_API_KEY by default.
# We'll also look for GEMINI_API_KEY just in case and map it if present.
# (Prefer GOOGLE_API_KEY; set both in .env if you like.)
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")  # change in .env if you like

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
app.permanent_session_lifetime = timedelta(hours=8)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- Memory store per user-session (in-memory). For production, swap for Redis. ---
_session_memories = {}

def get_conversation(session_id: str) -> ConversationChain:
    """Return (and lazily create) a ConversationChain bound to a session's buffer memory."""
    if session_id not in _session_memories:
        memory = ConversationBufferMemory(return_messages=True)
        llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            temperature=0.7,
            # You can tweak other params like max_output_tokens if needed.
        )
        chain = ConversationChain(llm=llm, memory=memory, verbose=False)
        _session_memories[session_id] = chain
    return _session_memories[session_id]

@app.before_request
def ensure_session():
    # Make sure we have a stable session id
    session.permanent = True
    if "sid" not in session:
        # A simple opaque id
        session["sid"] = os.urandom(16).hex()

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Empty message."}), 400

    chain = get_conversation(session["sid"])
    try:
        # ConversationChain expects plain text prompt; memory handles history.
        reply = chain.predict(input=user_message)
        return jsonify({"response": reply})
    except Exception as e:
        return jsonify({"error": f"LLM error: {e}"}), 500

@app.route("/reset", methods=["POST"])
def reset():
    sid = session.get("sid")
    if sid and sid in _session_memories:
        del _session_memories[sid]
    return jsonify({"ok": True, "message": "Conversation reset."})

if __name__ == "__main__":
    # For local dev only; use gunicorn/uvicorn in production
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
