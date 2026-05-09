"""
FastAPI — Intelligent Recruitment & Workforce Screening System
Powered by Groq (llama-3.1-8b-instant)

Endpoints:
  POST /screening/       - raw PDF upload  (JD from disk fallback)
  POST /screening/text/  - pre-extracted resume + JD text/parsed JSON  ← preferred
  POST /jd/analyze/      - parse a JD; returns structured requirements JSON

Scoring weights (deterministic):
  Skills Match      40 %
  Experience Match  30 %
  Department Fit    20 %
  Certifications    10 %

Key stability features for 10+ resume batches:
  - JD is parsed ONCE by the UI and sent as jd_parsed; analyze_jd() is skipped
  - Every result dict is deep-copied before returning
  - Fake/placeholder names are detected and replaced with the filename stem
  - All candidate fields are validated and sanitised before storing
  - Inter-agent delay (0.5s) prevents rapid successive Groq calls per resume
"""

from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.parsepdf import parse_pdf
from app.agents.resume_extractor_agent import analyze_resume
from app.agents.jd_extractor_agent import analyze_jd
from app.agents.candidate_evaluation_agent import evaluate_candidate
import copy
import json
import re
import time

app = FastAPI()


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def strip_json_fences(text: str) -> str:
    """Remove markdown code fences sometimes emitted by LLMs."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$",          "", text)
    return text.strip()


def _parse_llm_json(raw: str, label: str) -> tuple:
    """
    Parse LLM JSON output.
    Returns (dict, None) on success or (None, JSONResponse) on error.
    """
    if not raw or not raw.strip():
        return None, JSONResponse(
            status_code=500,
            content={"error": f"{label}: empty response from AI"},
        )
    # Check for agent-level error sentinel
    try:
        obj = json.loads(strip_json_fences(raw))
        if isinstance(obj, dict) and "error" in obj and len(obj) == 1:
            return None, JSONResponse(
                status_code=500,
                content={"error": f"{label} agent error: {obj['error']}"},
            )
        return obj, None
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[JSON error] {label}: {e} | raw[:300]: {raw[:300]}")
        return None, JSONResponse(
            status_code=500,
            content={"error": f"Failed to parse {label}: {str(e)}", "raw": str(raw[:300])},
        )


# ── Fake-name blocklist ────────────────────────────────────────────────────────
_FAKE_NAMES = {
    "john doe", "jane doe", "unknown candidate", "unknown", "candidate",
    "sample candidate", "test", "test user", "your name", "name here",
    "first last", "full name", "ravi kumar", "alex johnson", "placeholder",
    "resume", "applicant",
}

def _is_fake_name(name: str) -> bool:
    """Return True if the name looks like a placeholder or prompt-example value."""
    return not name or name.strip().lower() in _FAKE_NAMES


def _filename_to_name(filename: str) -> str:
    """Convert 'John_Smith_Resume.pdf' → 'John Smith Resume'."""
    stem = filename.rsplit(".", 1)[0]
    return re.sub(r"[_\-]+", " ", stem).strip()


# ── Candidate data validator ──────────────────────────────────────────────────
def _validate_candidate(candidate: dict, filename: str) -> dict:
    """
    Sanitise extracted candidate dict.
    - Replaces fake/missing names with the filename stem.
    - Ensures all list fields are actually lists.
    - Coerces work_experience to int or None.
    Returns a sanitised deep-copy.
    """
    c = copy.deepcopy(candidate)

    # Name
    raw_name = (c.get("name") or "").strip()
    if _is_fake_name(raw_name):
        fallback = _filename_to_name(filename)
        print(f"[Validate] Fake/missing name '{raw_name}' → using filename: '{fallback}'")
        c["name"] = fallback
    else:
        c["name"] = raw_name

    # Skills — must be a list of strings
    if not isinstance(c.get("skills"), list):
        c["skills"] = []
    c["skills"] = [str(s) for s in c["skills"] if s]

    # Certifications
    if not isinstance(c.get("certifications"), list):
        c["certifications"] = []

    # Projects
    if not isinstance(c.get("projects"), list):
        c["projects"] = []

    # work_experience → int or None
    exp = c.get("work_experience")
    if exp is not None:
        try:
            c["work_experience"] = int(float(str(exp)))
        except (ValueError, TypeError):
            c["work_experience"] = None

    return c


def _validate_feedback(feedback: dict, candidate_name: str) -> dict:
    """
    Sanitise AI evaluation feedback.
    - Replaces fake/missing candidate_name with the already-validated name.
    - Ensures list fields are lists.
    """
    f = copy.deepcopy(feedback)

    # Always override the AI's candidate_name with the one we validated in step 1
    f["candidate_name"] = candidate_name

    for key in ("strengths", "weaknesses"):
        if not isinstance(f.get(key), list):
            f[key] = []
        f[key] = [str(x) for x in f[key] if x]

    f.setdefault("reason",         "")
    f.setdefault("recommendation", "")
    f.setdefault("department_fit", "")

    return f


# ══════════════════════════════════════════════════════════════════════════════
# Deterministic Scoring Engine
# ══════════════════════════════════════════════════════════════════════════════

def _normalize(s: str) -> str:
    return s.lower().strip()


def _skills_match(candidate_skills: list, required_skills: list) -> tuple:
    """
    Return (matched, missing, score_0_to_1).
    Uses substring matching to handle equivalent terms.
    """
    if not required_skills:
        return [], [], 0.5
    cand_norm = [_normalize(s) for s in candidate_skills]
    matched, missing = [], []
    for req in required_skills:
        req_n = _normalize(req)
        hit   = any(req_n in cn or cn in req_n for cn in cand_norm)
        (matched if hit else missing).append(req)
    return matched, missing, len(matched) / len(required_skills)


def calculate_score(candidate: dict, jd: dict) -> dict:
    """
    Deterministic scoring.  Weights: Skills 40% | Experience 30% | Dept 20% | Certs 10%
    """
    # Skills (40%)
    matched, missing, skill_score = _skills_match(
        candidate.get("skills") or [],
        jd.get("skills") or [],
    )

    # Experience (30%)
    exp     = candidate.get("work_experience") or 0
    min_exp = jd.get("min_work_experience") or 0
    max_exp = jd.get("max_work_experience") or (min_exp + 3) or 3
    if min_exp <= exp <= max_exp:
        exp_score = 1.0
    elif exp < min_exp:
        exp_score = max(0.0, 1.0 - (min_exp - exp) / max(min_exp, 1))
    else:
        exp_score = max(0.5, 1.0 - (exp - max_exp) / (max_exp + 2))

    # Department fit (20%)
    cand_dept = _normalize(candidate.get("department") or "")
    jd_dept   = _normalize(jd.get("department") or "")
    if cand_dept and jd_dept:
        dept_score = 1.0 if (cand_dept in jd_dept or jd_dept in cand_dept) else 0.4
    else:
        dept_score = 0.5

    # Certifications (10%)
    cert_score = 1.0 if candidate.get("certifications") else 0.2

    total     = skill_score*0.40 + exp_score*0.30 + dept_score*0.20 + cert_score*0.10
    match_pct = round(total * 100)

    if match_pct >= 70:
        status = "Selected"
    elif match_pct >= 45:
        status = "Moderate Fit"
    else:
        status = "Rejected"

    return {
        "match_percentage":  match_pct,
        "candidate_status":  status,
        "matched_skills":    matched,
        "missing_skills":    missing,
        "score_breakdown": {
            "skills_score":        round(skill_score  * 100),
            "experience_score":    round(exp_score    * 100),
            "department_score":    round(dept_score   * 100),
            "certification_score": round(cert_score   * 100),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline  (one independent call per resume)
# ══════════════════════════════════════════════════════════════════════════════

def _run_screening_pipeline(
    resume_text: str,
    jd_text:    Optional[str]  = None,
    jd_parsed:  Optional[dict] = None,   # pre-parsed JD — skips analyze_jd() API call
    filename:   str            = "resume.pdf",
) -> JSONResponse:
    """
    Full isolated pipeline for a single resume.

    Name resolution priority:
      1. Extracted name from resume text  (most reliable)
      2. Filename stem                    (safe fallback)
    AI feedback candidate_name is ALWAYS overridden by the above.

    JD resolution priority:
      1. jd_parsed dict  (no API call needed — use when UI sends pre-parsed JD)
      2. jd_text string  (triggers analyze_jd() API call)
      3. Disk fallback   (resources/job_description.pdf)
    """
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"[Pipeline] START  file='{filename}'")

    # ── Step 1: Extract candidate ─────────────────────────────────────────────
    candidate_raw = analyze_resume(resume_text, filename=filename)
    candidate, err = _parse_llm_json(candidate_raw, "resume extraction")
    if err:
        print(f"[Pipeline] FAIL  resume extraction for '{filename}'")
        return err

    candidate = _validate_candidate(candidate, filename)
    final_name = candidate["name"]
    print(f"[Pipeline] Extracted & validated name: '{final_name}'")

    # Small delay between Groq calls to ease rate-limit pressure
    time.sleep(0.5)

    # ── Step 2: Resolve JD ───────────────────────────────────────────────────
    if jd_parsed:
        jd = copy.deepcopy(jd_parsed)
        print(f"[Pipeline] Using pre-parsed JD (no API call) — role: {jd.get('job_role')}")
    else:
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
            print(f"[Pipeline] FAIL  JD extraction for '{filename}'")
            return err
        jd = copy.deepcopy(jd)
        print(f"[Pipeline] JD extracted via API — role: {jd.get('job_role')}")
        time.sleep(0.5)

    # ── Step 3: Deterministic scoring ────────────────────────────────────────
    scores = calculate_score(candidate, jd)
    print(f"[Pipeline] Score: {scores['match_percentage']}%  |  {scores['candidate_status']}")

    # Small delay before evaluation call
    time.sleep(0.5)

    # ── Step 4: AI qualitative feedback ──────────────────────────────────────
    feedback_raw = evaluate_candidate(
        json.dumps(candidate, indent=2),
        json.dumps(jd, indent=2),
    )
    feedback, err = _parse_llm_json(feedback_raw, "evaluation")
    if err:
        print(f"[Pipeline] FAIL  evaluation for '{filename}'")
        return err

    # Always override AI's candidate_name with our validated name
    feedback = _validate_feedback(feedback, final_name)
    print(f"[Pipeline] Evaluation OK  |  dept_fit: {feedback.get('department_fit')}")

    # ── Step 5: Merge (all fields are fresh copies) ──────────────────────────
    result = {
        "candidate_name":   final_name,
        "department_fit":   feedback.get("department_fit") or candidate.get("department") or "—",
        "strengths":        list(feedback.get("strengths") or []),
        "weaknesses":       list(feedback.get("weaknesses") or []),
        "reason":           str(feedback.get("reason") or ""),
        "recommendation":   str(feedback.get("recommendation") or ""),
        "candidate_status": scores["candidate_status"],
        "match_percentage": scores["match_percentage"],
        "experience":       candidate.get("work_experience"),
        "matched_skills":   list(scores["matched_skills"]),
        "missing_skills":   list(scores["missing_skills"]),
        "score_breakdown":  dict(scores["score_breakdown"]),
        "education":        candidate.get("education"),
        "certifications":   list(candidate.get("certifications") or []),
        "source_file":      filename,
    }
    print(f"[Pipeline] DONE  '{final_name}' | {result['match_percentage']}% | {result['candidate_status']}")
    print(f"{sep}\n")
    return JSONResponse(content=copy.deepcopy(result))


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/screening/")
async def upload_resume(resume: UploadFile):
    """Raw PDF upload endpoint — uses disk JD fallback."""
    print(f"[API] /screening/  file='{resume.filename}'")
    return _run_screening_pipeline(
        parse_pdf(resume.file),
        filename=resume.filename or "upload.pdf",
    )


class ResumeTextRequest(BaseModel):
    resume_text: str
    jd_text:     Optional[str]  = None
    jd_parsed:   Optional[dict] = None   # Pre-parsed JD JSON from /jd/analyze/ — saves 1 Groq call per resume
    filename:    str            = "resume.pdf"


@app.post("/screening/text/")
async def screen_resume_text(request: ResumeTextRequest):
    """
    Primary endpoint for Streamlit UI.
    Send jd_parsed (from st.session_state.jd_details) to skip per-resume JD analysis.
    """
    print(f"[API] /screening/text/  file='{request.filename}'")
    return _run_screening_pipeline(
        request.resume_text,
        jd_text   = request.jd_text,
        jd_parsed = request.jd_parsed,
        filename  = request.filename,
    )


class JDTextRequest(BaseModel):
    jd_text: str


@app.post("/jd/analyze/")
async def analyze_jd_endpoint(request: JDTextRequest):
    """Parse a JD and return structured requirements JSON. Called ONCE per session."""
    print(f"[API] /jd/analyze/  len={len(request.jd_text)}")
    raw    = analyze_jd(request.jd_text)
    result, err = _parse_llm_json(raw, "JD analysis")
    if err:
        return err
    return JSONResponse(content=result)