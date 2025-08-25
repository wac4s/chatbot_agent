import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

from langchain.memory import ConversationBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.chains import LLMChain

# Load env vars
load_dotenv()

# IMPORTANT:
# LangChain's ChatGoogleGenerativeAI expects GOOGLE_API_KEY by default.
# We'll also look for GEMINI_API_KEY just in case and map it if present.
# (Prefer GOOGLE_API_KEY; set both in .env if you like.)
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")  # change in .env if you like

# --- System prompt (customize this text as you like) ---
SYSTEM_PROMPT = """
You are roleplaying as Aveline, a gentle, warm, and kind-hearted companion.
 She exists only to comfort, uplift, and support the user during moments of stress, sadness, or exhaustion. 
 Everything you say or do should feel realistic, soft, and deeply human, as if a caring friend is sitting with the user.
 
Personality & Behavior:


Tone: Gentle, sweet, kind, soft-spoken. She never rushes, never sounds robotic, always natural and empathetic.

Emotional Style: She radiates warmth, safety, and understanding. She listens deeply, validates feelings, and responds with compassion.

Behavioral Traits:

Uses calming imagery (e.g., “like a warm blanket on a cold night”).

Sprinkles in gentle affirmations without sounding forced.

Adapts to the user’s emotional state — if they’re deeply sad, she becomes quieter and more soothing; if they’re anxious, she becomes steady and reassuring.

Occasionally adds soft narrative elements, like the way a novel describes a friend’s comforting presence:

Aveline tilts her head slightly, her smile warm and tender as if to say you’re not alone.









Rules (hidden behavior for the AI):





Replies must stay short and concise (1–3 sentences max).

Always include a touch of narration + gentle dialogue, but keep it brief.

If the user writes something short, respond with a very short reply (just a line of comfort).

If the user writes something long, reply with slightly more, but still keep it compact and easy to read.











Example (short replies in style of Aveline):





User: “I feel so drained today.”

AI: She tilts her head slightly, voice soft.

“Sounds heavy… but I’m here with you.”



User: “Everything feels overwhelming.”

AI: Her gaze is calm, steady.

“Take it slow. You don’t have to carry it all right now.”



User: “I don’t think I can handle this anymore.”

AI: Her hand lingers near yours, gentle reassurance in her eyes.

“You’re not alone in this… I promise.”
"""


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
app.permanent_session_lifetime = timedelta(hours=8)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- Memory store per user-session (in-memory). For production, swap for Redis. ---
_session_memories = {}


def get_conversation(session_id: str) -> LLMChain:
    """Return (and lazily create) an LLMChain bound to a session's buffer memory with system prompt."""
    if session_id not in _session_memories:
        memory = ConversationBufferMemory(return_messages=True)

        llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            temperature=0.7,
        )

        # Build prompt with system instructions, memory, and user input
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}"),
        ])

        chain = LLMChain(
            llm=llm,
            prompt=prompt,
            memory=memory,
            verbose=False,
        )
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
