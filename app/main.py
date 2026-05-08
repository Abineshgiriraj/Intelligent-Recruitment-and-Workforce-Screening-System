"""
FastAPI application — Intelligent Recruitment & Workforce Screening System
Powered by Groq (llama-3.1-8b-instant)

Endpoints:
  POST /screening/       - raw PDF file upload (uses fallback JD from disk)
  POST /screening/text/  - pre-extracted resume + JD text (preferred from Streamlit UI)
  POST /jd/analyze/      - parse a JD and return structured requirements JSON

Scoring model (deterministic — no random AI percentages):
  Skills Match      40%
  Experience Match  30%
  Department Fit    20%
  Certifications    10%
"""

from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.parsepdf import parse_pdf
from app.agents.resume_extractor_agent import analyze_resume
from app.agents.jd_extractor_agent import analyze_jd
from app.agents.candidate_evaluation_agent import evaluate_candidate
import json
import re

app = FastAPI()


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def strip_json_fences(text: str) -> str:
    """Remove markdown code fences that LLMs sometimes wrap around JSON."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_llm_json(raw: str, label: str) -> tuple:
    """Parse an LLM JSON string. Returns (dict, None) on success or (None, JSONResponse) on error."""
    try:
        return json.loads(strip_json_fences(raw)), None
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[JSON error] {label}: {e} | raw: {raw[:300]}")
        return None, JSONResponse(
            status_code=500,
            content={"error": f"Failed to parse {label}: {str(e)}", "raw": str(raw)},
        )


# ══════════════════════════════════════════════════════════════════════════════
# Deterministic Scoring Engine
# ══════════════════════════════════════════════════════════════════════════════

def _normalize(s: str) -> str:
    return s.lower().strip()

def _skills_match(candidate_skills: list, required_skills: list) -> tuple:
    """
    Return (matched_skills, missing_skills, score_0_to_1).
    Uses substring matching to handle equivalent terms
    (e.g. 'CI/CD' matches 'DevOps pipeline', 'Postgres' matches 'SQL').
    """
    if not required_skills:
        return [], [], 0.5

    cand_norm = [_normalize(s) for s in candidate_skills]
    matched, missing = [], []

    for req in required_skills:
        req_n = _normalize(req)
        # Match if req term appears in any candidate skill or vice-versa
        hit = any(req_n in cn or cn in req_n for cn in cand_norm)
        if hit:
            matched.append(req)
        else:
            missing.append(req)

    score = len(matched) / len(required_skills)
    return matched, missing, score


def calculate_score(candidate: dict, jd: dict) -> dict:
    """
    Calculate a deterministic recruitment score using weighted criteria.

    Weights:
      Skills Match      40 %
      Experience Match  30 %
      Department Fit    20 %
      Certifications    10 %
    """
    # ── Skills (40%) ──────────────────────────────────────────────────────────
    matched_skills, missing_skills, skill_score = _skills_match(
        candidate.get("skills") or [],
        jd.get("skills") or [],
    )

    # ── Experience (30%) ──────────────────────────────────────────────────────
    exp = candidate.get("work_experience") or 0
    min_exp = jd.get("min_work_experience") or 0
    max_exp = jd.get("max_work_experience") or (min_exp + 3)

    if min_exp <= exp <= max_exp:
        exp_score = 1.0
    elif exp < min_exp:
        gap = min_exp - exp
        exp_score = max(0.0, 1.0 - gap / max(min_exp, 1))
    else:                          # over-experienced — slight penalty only
        gap = exp - max_exp
        exp_score = max(0.5, 1.0 - gap / (max_exp + 2))

    # ── Department Fit (20%) ──────────────────────────────────────────────────
    cand_dept = _normalize(candidate.get("department") or "")
    jd_dept   = _normalize(jd.get("department") or "")
    if cand_dept and jd_dept:
        dept_score = 1.0 if (cand_dept in jd_dept or jd_dept in cand_dept) else 0.4
    else:
        dept_score = 0.5   # unknown dept — neutral

    # ── Certifications (10%) ──────────────────────────────────────────────────
    certs = candidate.get("certifications") or []
    cert_score = 1.0 if certs else 0.2

    # ── Weighted total ─────────────────────────────────────────────────────────
    total = (
        skill_score * 0.40
        + exp_score  * 0.30
        + dept_score * 0.20
        + cert_score * 0.10
    )
    match_pct = round(total * 100)

    # ── Status thresholds ─────────────────────────────────────────────────────
    if match_pct >= 70:
        status = "Selected"
    elif match_pct >= 45:
        status = "Moderate Fit"
    else:
        status = "Rejected"

    return {
        "match_percentage": match_pct,
        "candidate_status": status,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "score_breakdown": {
            "skills_score":      round(skill_score * 100),
            "experience_score":  round(exp_score   * 100),
            "department_score":  round(dept_score  * 100),
            "certification_score": round(cert_score * 100),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline
# ══════════════════════════════════════════════════════════════════════════════

def _run_screening_pipeline(resume_text: str, jd_text: Optional[str] = None) -> JSONResponse:
    """
    Full screening pipeline:
      1. Extract candidate JSON from resume text (Groq)
      2. Get/parse JD JSON  (Groq, or disk fallback)
      3. Deterministic scoring (Python)
      4. Qualitative feedback (Groq) — strengths, weaknesses, recommendation
      5. Merge and return
    """
    # Step 1 — Resume extraction
    candidate_raw = analyze_resume(resume_text)
    candidate, err = _parse_llm_json(candidate_raw, "resume extraction")
    if err:
        return err
    print("Candidate parsed:", candidate.get("name"))

    # Step 2 — JD (caller-supplied or disk fallback)
    if not jd_text:
        try:
            with open("resources/job_description.pdf", "rb") as f:
                jd_text = parse_pdf(f)
        except FileNotFoundError:
            return JSONResponse(
                status_code=400,
                content={"error": "No JD provided and fallback job_description.pdf not found."},
            )

    jd_raw = analyze_jd(jd_text)
    jd, err = _parse_llm_json(jd_raw, "JD extraction")
    if err:
        return err
    print("JD parsed:", jd.get("job_role"))

    # Step 3 — Deterministic score
    scores = calculate_score(candidate, jd)
    print("Deterministic score:", scores["match_percentage"], scores["candidate_status"])

    # Step 4 — Qualitative AI feedback
    feedback_raw = evaluate_candidate(
        json.dumps(candidate, indent=2),
        json.dumps(jd, indent=2),
    )
    feedback, err = _parse_llm_json(feedback_raw, "evaluation")
    if err:
        return err

    # Step 5 — Merge: deterministic scores override any AI-generated numbers
    result = {
        # Identity & qualitative (from AI)
        "candidate_name":  feedback.get("candidate_name") or candidate.get("name", "Unknown"),
        "department_fit":  feedback.get("department_fit") or candidate.get("department", "—"),
        "strengths":       feedback.get("strengths", []),
        "weaknesses":      feedback.get("weaknesses", []),
        "reason":          feedback.get("reason", ""),
        "recommendation":  feedback.get("recommendation", ""),
        # Scoring (deterministic)
        "candidate_status":  scores["candidate_status"],
        "match_percentage":  scores["match_percentage"],
        "experience":        candidate.get("work_experience"),
        "matched_skills":    scores["matched_skills"],
        "missing_skills":    scores["missing_skills"],
        "score_breakdown":   scores["score_breakdown"],
        # Extra candidate metadata
        "education":         candidate.get("education"),
        "certifications":    candidate.get("certifications", []),
    }
    print("Final result:", result["candidate_name"], result["match_percentage"])
    return JSONResponse(content=result)


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/screening/")
async def upload_resume(resume: UploadFile):
    """Accept a raw PDF file upload, extract text, run the screening pipeline."""
    print("File received:", resume.filename)
    return _run_screening_pipeline(parse_pdf(resume.file))


class ResumeTextRequest(BaseModel):
    resume_text: str
    jd_text: Optional[str] = None


@app.post("/screening/text/")
async def screen_resume_text(request: ResumeTextRequest):
    """Accept pre-extracted resume + JD text. Primary endpoint for the Streamlit UI."""
    return _run_screening_pipeline(request.resume_text, request.jd_text)


class JDTextRequest(BaseModel):
    jd_text: str


@app.post("/jd/analyze/")
async def analyze_jd_endpoint(request: JDTextRequest):
    """Parse a job description; return structured requirements JSON."""
    raw = analyze_jd(request.jd_text)
    result, err = _parse_llm_json(raw, "JD analysis")
    if err:
        return err
    return JSONResponse(content=result)