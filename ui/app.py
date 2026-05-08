"""
AI Resume Screener — Streamlit UI
Powered by Groq (llama-3.1-8b-instant) | Textile & Manufacturing HR Focus

Flow:
  STEP 1 → Upload Job Description (PDF / TXT / DOCX)
            → Extract JD text locally (cached)
            → Parse JD via /jd/analyze/ (one API call, stored in session_state)
            → Display JD summary: department, role, skills, experience
  STEP 2 → Upload one or more resumes (PDF)
            → Extract text locally (cached per file hash)
            → On "Analyze" click → call /screening/text/ with resume + JD text
            → Store results in session_state (no re-calls on rerun)
  STEP 3 → Display ranked results + Top 3 podium
            → Reset clears results but keeps JD loaded
"""

import hashlib
import io
import json

import PyPDF2
import requests
import streamlit as st

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="📋",
    layout="wide",
)

BACKEND_URL = "http://localhost:8000"

# ── cached text extractors (keyed on raw bytes — never re-run on widget reruns) ─

@st.cache_data(show_spinner=False)
def _extract_pdf(file_bytes: bytes) -> str:
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as e:
        return f"[PDF error: {e}]"

@st.cache_data(show_spinner=False)
def _extract_txt(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"[TXT error: {e}]"

@st.cache_data(show_spinner=False)
def _extract_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as e:
        return f"[DOCX error: {e}]"

def extract_text(file_bytes: bytes, filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        return _extract_pdf(file_bytes)
    elif ext == "txt":
        return _extract_txt(file_bytes)
    elif ext == "docx":
        return _extract_docx(file_bytes)
    return "[Unsupported file format]"

def file_hash(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# ── session state bootstrap ────────────────────────────────────────────────────
_defaults = {
    "jd_text": None,           # raw extracted JD text
    "jd_details": None,        # parsed JD JSON from /jd/analyze/
    "jd_hash": None,           # md5 of last uploaded JD bytes
    "results": {},             # {filename: {"status": ..., "data": ...}}
    "processed_hashes": {},    # {md5: result} — dedup cache across reruns
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def _reset_results():
    """Clear resume results but keep the JD loaded."""
    st.session_state.results = {}
    st.session_state.processed_hashes = {}

def _reset_all():
    """Clear everything including JD."""
    for k, v in _defaults.items():
        st.session_state[k] = v if not isinstance(v, dict) else {}


# ── header ─────────────────────────────────────────────────────────────────────
st.title("📋 AI Resume Screener")
st.caption("Powered by Groq · llama-3.1-8b-instant | Textile & Manufacturing HR")
st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Job Description Upload
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📄 Step 1: Upload Job Description")

jd_col, jd_btn_col = st.columns([4, 1])
with jd_col:
    jd_file = st.file_uploader(
        "Upload JD file (PDF, TXT, or DOCX)",
        type=["pdf", "txt", "docx"],
        key="jd_uploader",
        label_visibility="collapsed",
    )
with jd_btn_col:
    st.button("🗑️ Clear All", on_click=_reset_all, use_container_width=True,
              help="Clear JD and all resume results")

if jd_file:
    jd_bytes = jd_file.read()
    jd_h = file_hash(jd_bytes)

    # Only call API if this is a new/different JD file
    if jd_h != st.session_state.jd_hash:
        with st.spinner(f"Extracting and analyzing **{jd_file.name}**…"):
            jd_text = extract_text(jd_bytes, jd_file.name)

            if jd_text.startswith("["):
                st.error(f"Failed to extract JD text: {jd_text}")
            else:
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/jd/analyze/",
                        json={"jd_text": jd_text},
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        st.session_state.jd_text = jd_text
                        st.session_state.jd_details = resp.json()
                        st.session_state.jd_hash = jd_h
                        _reset_results()   # clear old resume results when JD changes
                        st.success("Job Description analyzed successfully!")
                    else:
                        st.error(f"JD analysis failed (HTTP {resp.status_code}): {resp.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not reach backend: {e}")

# Display parsed JD summary
if st.session_state.jd_details:
    jd = st.session_state.jd_details
    with st.container(border=True):
        st.markdown("#### 🏢 Job Description Summary")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Department:** {jd.get('department', '—')}")
            st.markdown(f"**Job Role:** {jd.get('job_role', '—')}")
        with c2:
            min_e = jd.get("min_work_experience", "?")
            max_e = jd.get("max_work_experience", "?")
            st.markdown(f"**Experience Required:** {min_e} – {max_e} years")
        with c3:
            skills = jd.get("skills", [])
            st.markdown(f"**No. of Required Skills:** {len(skills)}")

        if skills:
            st.markdown("**Required Skills:**")
            # Display as pill-like inline code spans
            st.markdown("  ".join(f"`{s}`" for s in skills))

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Resume Upload & Analysis
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.jd_details:
    st.info("⬆️ Please upload and process a Job Description first (Step 1).")
else:
    st.subheader("📂 Step 2: Upload Resumes")

    uploaded_files = st.file_uploader(
        "Upload one or more PDF resumes",
        type="pdf",
        accept_multiple_files=True,
        key="resume_uploader",
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)} resume(s) ready to analyze**")

        btn_col1, btn_col2 = st.columns([3, 1])
        with btn_col1:
            analyze_clicked = st.button(
                "🔍 Analyze Resumes",
                type="primary",
                use_container_width=True,
            )
        with btn_col2:
            st.button(
                "🔄 Reset Results",
                on_click=_reset_results,
                use_container_width=True,
                help="Keep the JD but clear all resume results",
            )

        # ── API calls ONLY inside this block ──────────────────────────────────
        if analyze_clicked:
            progress = st.progress(0.0, text="Starting analysis…")
            total = len(uploaded_files)

            for idx, uf in enumerate(uploaded_files):
                progress.progress(idx / total, text=f"Analyzing **{uf.name}** ({idx+1}/{total})…")

                raw_bytes = uf.read()
                h = file_hash(raw_bytes)

                # Dedup: use cached result if same file was already processed
                if h in st.session_state.processed_hashes:
                    st.session_state.results[uf.name] = st.session_state.processed_hashes[h]
                    continue

                # Extract text locally (cached by @st.cache_data)
                resume_text = extract_text(raw_bytes, uf.name)

                if resume_text.startswith("["):
                    result = {"status": "error", "message": resume_text}
                else:
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/screening/text/",
                            json={
                                "resume_text": resume_text,
                                "jd_text": st.session_state.jd_text,
                            },
                            timeout=120,
                        )
                        if response.status_code == 200:
                            result = {"status": "success", "data": response.json()}
                        else:
                            result = {
                                "status": "error",
                                "message": f"HTTP {response.status_code}: {response.text}",
                            }
                    except requests.exceptions.RequestException as e:
                        result = {"status": "error", "message": str(e)}

                st.session_state.results[uf.name] = result
                st.session_state.processed_hashes[h] = result

            progress.progress(1.0, text="✅ Analysis complete!")

    else:
        st.info("👆 Upload PDF resumes above to get started.")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Results: Top 3 Podium + Full Ranking
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.results:
    st.markdown("---")

    # Separate successes from errors, sort by skill_match_percentage desc
    successful = [
        (name, r) for name, r in st.session_state.results.items()
        if r["status"] == "success"
    ]
    failed = [
        (name, r) for name, r in st.session_state.results.items()
        if r["status"] == "error"
    ]
    successful.sort(
        key=lambda x: x[1]["data"].get("skill_match_percentage", 0),
        reverse=True,
    )

    # ── Top 3 Podium ──────────────────────────────────────────────────────────
    if successful:
        st.subheader("🏆 Top Candidates")
        medals = ["🥇", "🥈", "🥉"]
        top3 = successful[:3]
        podium_cols = st.columns(len(top3))

        for i, (filename, res) in enumerate(top3):
            data = res["data"]
            pct = data.get("skill_match_percentage", 0)
            status = data.get("candidate_status", "")
            name = data.get("candidate_name") or filename.replace(".pdf", "")
            dept = data.get("department_fit", "—")
            exp = data.get("experience", "—")

            with podium_cols[i]:
                with st.container(border=True):
                    st.markdown(f"### {medals[i]}")
                    st.markdown(f"**{name}**")
                    st.metric("Match Score", f"{pct}%")
                    if status == "Selected":
                        st.success("✅ Selected")
                    else:
                        st.error("❌ Rejected")
                    st.markdown(f"🏢 `{dept}` · 🗓 `{exp} yrs`")

        st.markdown("---")

        # ── Full Ranked Results ────────────────────────────────────────────────
        st.subheader("📊 Full Analysis — Ranked by Match Score")

        for rank, (filename, res) in enumerate(successful, 1):
            data = res["data"]
            pct = data.get("skill_match_percentage", "?")
            status = data.get("candidate_status", "")
            badge = medals[rank - 1] if rank <= 3 else f"#{rank}"
            label_color = "🟢" if status == "Selected" else "🔴"

            with st.expander(
                f"{badge} {filename}  ·  {label_color} {status}  ·  {pct}% match",
                expanded=(rank == 1),
            ):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Skills Match", f"{pct}%")
                with c2:
                    st.metric("Experience", f"{data.get('experience', 'N/A')} yrs")
                with c3:
                    st.metric("Department Fit", data.get("department_fit", "N/A"))

                if status == "Selected":
                    st.markdown("### ✅ :green[**Selected**]")
                else:
                    st.markdown("### ❌ :red[**Rejected**]")

                st.subheader("💬 Evaluation")
                st.write(data.get("reason", "—"))

                if data.get("recommendation"):
                    st.info(f"💡 {data['recommendation']}")

                skill_col, miss_col = st.columns(2)
                with skill_col:
                    matched = data.get("matched_skills", [])
                    if matched:
                        st.markdown("**✅ Matched Skills**")
                        st.markdown("  ·  ".join(f"`{s}`" for s in matched))
                with miss_col:
                    missing = data.get("missing_skills", [])
                    if missing:
                        st.markdown("**❌ Missing Skills**")
                        st.markdown("  ·  ".join(f"`{s}`" for s in missing))

                if st.checkbox("Show raw API response", key=f"debug_{filename}_{rank}", value=False):
                    st.json(data)

    # ── Failed files ───────────────────────────────────────────────────────────
    if failed:
        st.markdown("---")
        st.subheader("⚠️ Errors")
        for filename, res in failed:
            with st.expander(f"❌ {filename}"):
                st.error(res["message"])
