from groq import Groq
from dotenv import load_dotenv
import os
from app.prompts import EXTRACT_CANDIDATE_DETAILS
import json
import time

load_dotenv()
client = Groq(api_key=os.getenv("groq_api"))
MODEL = "llama-3.1-8b-instant"


def analyze_resume(text: str) -> str:
    """
    Extract structured candidate details from resume text using Groq (llama3-8b-8192).
    Only sends the first 4000 chars to stay well within token limits.
    """
    # Trim to avoid hitting context limits; key info is almost always near the top
    trimmed = text[:4000].strip()
    prompt = EXTRACT_CANDIDATE_DETAILS.format(resume_text=trimmed)
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            result = response.choices[0].message.content
            print("Resume Extractor Agent response:", result)
            return result
        except Exception as e:
            err = str(e)
            print(f"Resume Extractor attempt {attempt + 1} failed: {err}")
            if "rate_limit" in err.lower() and attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                return json.dumps({"error": err})