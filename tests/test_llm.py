import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
key = os.getenv("GEMINI_API_KEY")

if not key:
    print("Key nahi mili. .env file check karo.")
else:
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents="Reply with exactly one word: Hello",
    )
    print("LLM ka jawab:", response.text)