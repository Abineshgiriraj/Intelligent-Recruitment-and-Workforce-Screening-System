"""
FastAPI application for agentic resume screening using Groq.
Endpoints:
  POST /screening/       - accepts a raw PDF file upload (fallback, reads JD from disk)
  POST /screening/text/  - accepts pre-extracted resume + JD text as JSON (preferred)
  POST /jd/analyze/      - parses a job description and returns structured JSON
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


# ── helpers ────────────────────────────────────────────────────────────────────

def strip_json_fences(text: str) -> str:
    """Remove markdown code fences that LLMs sometimes wrap around JSON."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_llm_json(raw: str, label: str) -> tuple[dict | None, JSONResponse | None]:
    """Parse an LLM response string to dict. Returns (dict, None) or (None, error response)."""
    try:
        return json.loads(strip_json_fences(raw)), None
    except (json.JSONDecodeError, TypeError) as e:
        print(f"JSON parse error [{label}]:", e, "| raw:", raw)
        return None, JSONResponse(
            status_code=500,
            content={"error": f"Failed to parse {label} response: {str(e)}", "raw": str(raw)},
        )


def _run_screening_pipeline(resume_text: str, jd_text: Optional[str] = None) -> JSONResponse:
    """
    Run all 3 Groq agents and return a JSONResponse.
    If jd_text is None, falls back to reading resources/job_description.pdf.
    """
    # Step 1: Extract candidate details from resume
    candidate_raw = analyze_resume(resume_text)
    print("Candidate details raw:", candidate_raw)

    # Step 2: Get JD text (from caller or from disk as fallback)
    if not jd_text:
        try:
            with open("resources/job_description.pdf", "rb") as f:
                jd_text = parse_pdf(f)
        except FileNotFoundError:
            return JSONResponse(
                status_code=400,
                content={"error": "No JD provided and no fallback job_description.pdf found."},
            )

    # Step 3: Extract JD requirements
    jd_raw = analyze_jd(jd_text)
    print("JD details raw:", jd_raw)

    # Step 4: Evaluate candidate against JD
    evaluation_raw = evaluate_candidate(candidate_raw, jd_raw)
    print("Evaluation result raw:", evaluation_raw)

    result, err = _parse_llm_json(evaluation_raw, "evaluation")
    if err:
        return err

    print("Parsed result:", result)
    return JSONResponse(content=result)


# ── endpoints ──────────────────────────────────────────────────────────────────

@app.post("/screening/")
async def upload_resume(resume: UploadFile):
    """Accept a raw PDF file upload, extract text, then run the screening pipeline."""
    print("Received resume file:", resume.filename)
    resume_text = parse_pdf(resume.file)
    print("PDF parsed, length:", len(resume_text))
    return _run_screening_pipeline(resume_text)


class ResumeTextRequest(BaseModel):
    resume_text: str          # Pre-extracted resume text (from Streamlit local parsing)
    jd_text: Optional[str] = None  # Pre-extracted JD text; falls back to disk if omitted


@app.post("/screening/text/")
async def screen_resume_text(request: ResumeTextRequest):
    """
    Accept pre-extracted resume + JD text as JSON.
    Primary endpoint for the Streamlit UI — avoids re-uploading files on reruns.
    """
    print("Resume text length:", len(request.resume_text))
    return _run_screening_pipeline(request.resume_text, request.jd_text)


class JDTextRequest(BaseModel):
    jd_text: str  # Raw extracted JD text to parse


@app.post("/jd/analyze/")
async def analyze_jd_endpoint(request: JDTextRequest):
    """
    Parse a job description and return structured requirements JSON.
    Called by the Streamlit UI after the user uploads a JD file.
    """
    print("JD text length:", len(request.jd_text))
    raw = analyze_jd(request.jd_text)
    result, err = _parse_llm_json(raw, "JD analysis")
    if err:
        return err
    return JSONResponse(content=result)