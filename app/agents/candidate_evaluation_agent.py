from groq import Groq
from dotenv import load_dotenv
import os
from app.prompts import CANDIDATE_EVALUATION
import json
import time

load_dotenv()
client = Groq(api_key=os.getenv("groq_api"))
MODEL = "llama-3.1-8b-instant"


def evaluate_candidate(candidate_details: str, jd: str) -> str:
    """
    Evaluate a candidate against a job description using Groq (llama3-8b-8192).
    Both inputs are already compact JSON strings produced by the extractor agents.
    """
    prompt = CANDIDATE_EVALUATION.format(resume_json=candidate_details, jd_json=jd)
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            result = response.choices[0].message.content
            print("Candidate Evaluation Agent response:", result)
            return result
        except Exception as e:
            err = str(e)
            print(f"Candidate Evaluator attempt {attempt + 1} failed: {err}")
            if "rate_limit" in err.lower() and attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                return json.dumps({"error": err})