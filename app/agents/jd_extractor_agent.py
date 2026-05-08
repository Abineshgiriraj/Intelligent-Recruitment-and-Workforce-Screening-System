from groq import Groq
from dotenv import load_dotenv
import os
from app.prompts import EXTRACT_JD_DETAILS
import json
import time

load_dotenv()
client = Groq(api_key=os.getenv("groq_api"))
MODEL = "llama-3.1-8b-instant"


def analyze_jd(text: str) -> str:
    """
    Extract structured job requirements from a job description using Groq (llama3-8b-8192).
    """
    trimmed = text[:3000].strip()
    prompt = EXTRACT_JD_DETAILS.format(jd_text=trimmed)
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            result = response.choices[0].message.content
            print("JD Extractor Agent response:", result)
            return result
        except Exception as e:
            err = str(e)
            print(f"JD Extractor attempt {attempt + 1} failed: {err}")
            if "rate_limit" in err.lower() and attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                return json.dumps({"error": err})
