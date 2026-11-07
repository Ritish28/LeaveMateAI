import json
import os
import re
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY .env file me nahi mili.")
        _client = genai.Client(api_key=key)
    return _client


def ask_llm(prompt, retries=3):
    """LLM se plain text jawab leta hai. Server busy ho to thodi der ruk ke dobara try karta hai."""
    last_error = None
    for attempt in range(retries):
        try:
            response = _get_client().models.generate_content(model=MODEL, contents=prompt)
            return response.text or ""
        except Exception as e:
            last_error = e
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                break
            print("LLM error:", e)
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))  # 2 sec, phir 4 sec
    raise RuntimeError(f"LLM abhi available nahi hai: {last_error}")


def ask_llm_json(prompt):
    """
    LLM se JSON jawab leta hai aur dictionary me badalta hai.
    Agar JSON samajh na aaye to None deta hai (app crash nahi hoga).
    """
    text = ask_llm(prompt).strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None