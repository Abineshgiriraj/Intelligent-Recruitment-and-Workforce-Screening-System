from groq import Groq
from dotenv import load_dotenv
import os
import json
import time
import random
from app.prompts import CANDIDATE_EVALUATION

load_dotenv()
client = Groq(api_key=os.getenv("groq_api"))
MODEL  = "llama-3.1-8b-instant"


def evaluate_candidate(candidate_json: str, jd_json: str) -> str:
    """
    Generate qualitative feedback for a candidate against a JD using Groq.

    - Both inputs are compact JSON strings from the extractor agents.
    - Retries up to 3 times with exponential back-off + jitter.
    - Returns a raw JSON string (error sentinel on total failure).
    """
    prompt = CANDIDATE_EVALUATION.format(
        resume_json=candidate_json,
        jd_json=jd_json,
    )

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=600,
            )
            result = response.choices[0].message.content.strip()
            print(f"[Evaluator] attempt {attempt+1} OK — length {len(result)}")
            return result
        except Exception as e:
            err = str(e)
            print(f"[Evaluator] attempt {attempt+1} FAILED: {err}")
            if attempt < 2:
                wait = (5 ** (attempt + 1)) + random.uniform(0, 3)
                print(f"[Evaluator] waiting {wait:.1f}s before retry…")
                time.sleep(wait)
            else:
                return json.dumps({"error": f"Evaluator failed after 3 attempts: {err}"})