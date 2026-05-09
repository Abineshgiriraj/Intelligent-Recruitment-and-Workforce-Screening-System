from groq import Groq
from dotenv import load_dotenv
import os
import json
import time
import random
from app.prompts import EXTRACT_CANDIDATE_DETAILS

load_dotenv()
client = Groq(api_key=os.getenv("groq_api"))
MODEL  = "llama-3.1-8b-instant"


def analyze_resume(text: str, filename: str = "resume.pdf") -> str:
    """
    Extract structured candidate details from resume text using Groq.

    - Trims input to 4000 chars to stay within token limits.
    - Passes filename hint so the LLM has a last-resort name reference.
    - Retries up to 3 times with exponential back-off + jitter on rate-limit errors.
    - Returns a raw JSON string (may be an error sentinel on failure).
    """
    trimmed = text[:4000].strip()
    # Inject filename as a hint comment — helps when resume header is garbled
    hint    = f"# Source file: {filename}\n\n"
    prompt  = EXTRACT_CANDIDATE_DETAILS.format(resume_text=hint + trimmed)

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=800,
            )
            result = response.choices[0].message.content.strip()
            print(f"[ResumeExtractor] attempt {attempt+1} OK — length {len(result)}")
            return result
        except Exception as e:
            err = str(e)
            print(f"[ResumeExtractor] attempt {attempt+1} FAILED: {err}")
            if attempt < 2:
                # Exponential back-off with jitter: 5s, 12-15s
                wait = (5 ** (attempt + 1)) + random.uniform(0, 3)
                print(f"[ResumeExtractor] waiting {wait:.1f}s before retry…")
                time.sleep(wait)
            else:
                return json.dumps({"error": f"ResumeExtractor failed after 3 attempts: {err}"})