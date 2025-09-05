import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env (if present)
load_dotenv()

def get_ai_response(prompt: str) -> str:
    """
    Safe helper using environment variables.
    Uses the Responses API; returns a friendly message if misconfigured.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        return "Sorry, I couldn't get a response right now. (Missing OPENAI_API_KEY)"

    try:
        org_id = os.getenv("OPENAI_ORG_ID")
        project_id = os.getenv("OPENAI_PROJECT_ID")
        kwargs = {}
        if org_id:
            kwargs["organization"] = org_id
        if project_id:
            kwargs["project"] = project_id

        client = OpenAI(api_key=api_key, **kwargs)
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": [{"type": "text", "text": "You are a helpful AI character."}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]},
            ],
            temperature=0.7,
        )
        return (resp.output_text or "").strip()
    except Exception as e:
        name = e.__class__.__name__
        if "Authentication" in name:
            return "Sorry, I couldn't get a response right now. (AuthenticationError: check OPENAI_API_KEY / org / project / model access)"
        return f"Sorry, I couldn't get a response right now. ({name})"


# add waqas prompt
# ask AI to generate code with separate system prompt
