"""
AI Resume Screener — Recruiter Dashboard
Intelligent Recruitment & Workforce Screening System
Powered by Groq · llama-3.1-8b-instant | Textile & Manufacturing HR

Workflow:
  Step 1 → Upload JD (PDF/TXT/DOCX) → AI parses → JD summary card
  Step 2 → Upload resumes (PDF, multi) → local cached extraction
  Step 3 → Click Analyze → deterministic scoring + AI qualitative feedback
  Step 4 → Dashboard: aggregate stats → Top 3 podium → comparison table → detailed cards
"""

import hashlib
import io

import PyPDF2
import requests
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Recruitment Screener",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BACKEND_URL = "http://localhost:8000"

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    border-left: 4px solid #4A90D9;
}
.selected-badge  { color: #1a7a1a; font-weight: 700; }
.moderate-badge  { color: #b35c00; font-weight: 700; }
.rejected-badge  { color: #9e1c1c; font-weight: 700; }
.skill-chip {
    display: inline-block;
    background: #e8f0fe;
    color: #1a56cc;
    border-radius: 12px;
    padding: 2px 10px;
    margin: 2px;
    font-size: 0.82em;
}
.miss-chip {
    display: inline-block;
    background: #fde8e8;
    color: #9e1c1c;
    border-radius: 12px;
    padding: 2px 10px;
    margin: 2px;
    font-size: 0.82em;
}
</style>
""", unsafe_allow_html=True)


# ── Cached text extractors ─────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _pdf(b: bytes) -> str:
    try:
        r = PyPDF2.PdfReader(io.BytesIO(b))
        return "\n".join(p.extract_text() or "" for p in r.pages).strip()
    except Exception as e:
        return f"[PDF error: {e}]"

@st.cache_data(show_spinner=False)
def _txt(b: bytes) -> str:
    return b.decode("utf-8", errors="replace").strip()

@st.cache_data(show_spinner=False)
def _docx(b: bytes) -> str:
    try:
        from docx import Document
        return "\n".join(p.text for p in Document(io.BytesIO(b)).paragraphs).strip()
    except Exception as e:
        return f"[DOCX error: {e}]"

def extract_text(b: bytes, name: str) -> str:
    ext = name.lower().rsplit(".", 1)[-1]
    return {"pdf": _pdf, "txt": _txt, "docx": _docx}.get(ext, lambda _: "[Unsupported]")(b)

def fhash(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


# ── Session state ──────────────────────────────────────────────────────────────
DEFAULTS = {
    "jd_text": None, "jd_details": None, "jd_hash": None,
    "results": {}, "proc_hashes": {},
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

def _reset_results():
    st.session_state.results = {}
    st.session_state.proc_hashes = {}

def _reset_all():
    for k, v in DEFAULTS.items():
        st.session_state[k] = ({} if isinstance(v, dict) else v)


# ── Status helpers ─────────────────────────────────────────────────────────────
STATUS_COLOR = {"Selected": "🟢", "Moderate Fit": "🟡", "Rejected": "🔴"}
STATUS_MD = {
    "Selected":     "### ✅ :green[**Selected**]",
    "Moderate Fit": "### 🟡 :orange[**Moderate Fit**]",
    "Rejected":     "### ❌ :red[**Rejected**]",
}

def status_badge(s):
    return STATUS_COLOR.get(s, "⚪") + " " + (s or "—")

def chips(items, css_class="skill-chip"):
    if not items:
        return "—"
    return " ".join(f'<span class="{css_class}">{i}</span>' for i in items)


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
col_h1, col_h2 = st.columns([5, 1])
with col_h1:
    st.title("🏭 AI Recruitment Screener")
    st.caption("Intelligent Workforce Screening System · Textile & Manufacturing HR · Powered by Groq")
with col_h2:
    st.button("🗑️ Clear All", on_click=_reset_all, use_container_width=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — JD Upload
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📋 Step 1 — Upload Job Description")
jd_file = st.file_uploader(
    "Supported: PDF, TXT, DOCX",
    type=["pdf", "txt", "docx"],
    key="jd_uploader",
    label_visibility="collapsed",
)

if jd_file:
    jd_bytes = jd_file.read()
    jd_h = fhash(jd_bytes)

    if jd_h != st.session_state.jd_hash:
        with st.spinner(f"Analyzing **{jd_file.name}**…"):
            jd_text = extract_text(jd_bytes, jd_file.name)
            if jd_text.startswith("["):
                st.error(jd_text)
            else:
                try:
                    r = requests.post(f"{BACKEND_URL}/jd/analyze/",
                                      json={"jd_text": jd_text}, timeout=60)
                    if r.status_code == 200:
                        st.session_state.jd_text    = jd_text
                        st.session_state.jd_details = r.json()
                        st.session_state.jd_hash    = jd_h
                        _reset_results()
                        st.success("✅ Job Description analyzed!")
                    else:
                        st.error(f"JD analysis failed: {r.text}")
                except Exception as e:
                    st.error(f"Backend error: {e}")

# JD summary card
if st.session_state.jd_details:
    jd = st.session_state.jd_details
    with st.container(border=True):
        st.markdown("#### 🏢 Job Description Summary")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Department:** `{jd.get('department', '—')}`")
            st.markdown(f"**Role:** `{jd.get('job_role', '—')}`")
        with c2:
            mn = jd.get("min_work_experience", "?")
            mx = jd.get("max_work_experience", "?")
            st.markdown(f"**Experience:** `{mn} – {mx} years`")
            st.markdown(f"**Required Skills:** `{len(jd.get('skills', []))}`")
        with c3:
            skills = jd.get("skills", [])
            if skills:
                st.markdown("**Skills:**")
                st.markdown(chips(skills), unsafe_allow_html=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Resume Upload
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.jd_details:
    st.info("⬆️ Upload and analyze a Job Description first (Step 1).")
else:
    st.subheader("📂 Step 2 — Upload Resumes")
    uploaded_files = st.file_uploader(
        "Upload one or more PDF resumes",
        type="pdf",
        accept_multiple_files=True,
        key="resume_uploader",
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.caption(f"**{len(uploaded_files)} resume(s)** ready · "
                   f"Existing results: **{len(st.session_state.results)}**")

        btn1, btn2 = st.columns([3, 1])
        with btn1:
            analyze_clicked = st.button("🔍 Analyze All Resumes",
                                        type="primary", use_container_width=True)
        with btn2:
            st.button("🔄 Reset Results", on_click=_reset_results,
                      use_container_width=True)

        # ── API calls — ONLY triggered by button ──────────────────────────────
        if analyze_clicked:
            progress = st.progress(0.0, text="Starting…")
            total = len(uploaded_files)

            for idx, uf in enumerate(uploaded_files):
                progress.progress(idx / total,
                    text=f"Analyzing **{uf.name}** ({idx+1}/{total})…")

                raw = uf.read()
                h   = fhash(raw)

                if h in st.session_state.proc_hashes:
                    st.session_state.results[uf.name] = st.session_state.proc_hashes[h]
                    continue

                text = extract_text(raw, uf.name)
                if text.startswith("["):
                    result = {"status": "error", "message": text}
                else:
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/screening/text/",
                            json={"resume_text": text,
                                  "jd_text": st.session_state.jd_text},
                            timeout=120,
                        )
                        result = ({"status": "success", "data": resp.json()}
                                  if resp.status_code == 200
                                  else {"status": "error",
                                        "message": f"HTTP {resp.status_code}: {resp.text}"})
                    except Exception as e:
                        result = {"status": "error", "message": str(e)}

                st.session_state.results[uf.name] = result
                st.session_state.proc_hashes[h]   = result

            progress.progress(1.0, text="✅ Analysis complete!")
    else:
        if not st.session_state.results:
            st.info("👆 Upload PDF resumes above.")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Recruiter Dashboard Results
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.results:
    st.stop()

st.markdown("---")

# Partition results
successful = [
    (name, r) for name, r in st.session_state.results.items()
    if r["status"] == "success"
]
failed = [
    (name, r) for name, r in st.session_state.results.items()
    if r["status"] == "error"
]
successful.sort(
    key=lambda x: x[1]["data"].get("match_percentage", 0),
    reverse=True,
)

# ── Aggregate Stats ────────────────────────────────────────────────────────────
st.subheader("📊 Recruitment Overview")
total_c    = len(successful)
selected_c = sum(1 for _, r in successful if r["data"].get("candidate_status") == "Selected")
moderate_c = sum(1 for _, r in successful if r["data"].get("candidate_status") == "Moderate Fit")
rejected_c = sum(1 for _, r in successful if r["data"].get("candidate_status") == "Rejected")
avg_match  = (sum(r["data"].get("match_percentage", 0) for _, r in successful) // total_c
              if total_c else 0)

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Total Candidates", total_c)
s2.metric("✅ Selected",       selected_c)
s3.metric("🟡 Moderate Fit",   moderate_c)
s4.metric("❌ Rejected",        rejected_c)
s5.metric("Avg Match Score",   f"{avg_match}%")

st.markdown("---")

# ── Top 3 Podium ──────────────────────────────────────────────────────────────
if successful:
    st.subheader("🏆 Top Candidates")
    medals = ["🥇", "🥈", "🥉"]
    top3   = successful[:3]
    cols   = st.columns(len(top3))

    for i, (fname, res) in enumerate(top3):
        d = res["data"]
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"## {medals[i]}")
                st.markdown(f"**{d.get('candidate_name', fname)}**")
                st.metric("Match", f"{d.get('match_percentage', '?')}%")
                s = d.get("candidate_status", "")
                if s == "Selected":
                    st.success("✅ Selected")
                elif s == "Moderate Fit":
                    st.warning("🟡 Moderate Fit")
                else:
                    st.error("❌ Rejected")
                st.caption(f"🏢 {d.get('department_fit','—')}  ·  🗓 {d.get('experience','—')} yrs")
                rec = d.get("recommendation", "")
                if rec:
                    st.caption(f"💡 {rec[:120]}{'…' if len(rec)>120 else ''}")

st.markdown("---")

# ── Candidate Comparison Table ────────────────────────────────────────────────
st.subheader("📋 Candidate Comparison Table")

import pandas as pd

table_rows = []
for rank, (fname, res) in enumerate(successful, 1):
    d = res["data"]
    table_rows.append({
        "Rank":          rank,
        "Candidate":     d.get("candidate_name", fname),
        "Department":    d.get("department_fit", "—"),
        "Match %":       d.get("match_percentage", 0),
        "Status":        status_badge(d.get("candidate_status", "")),
        "Experience":    f"{d.get('experience', '?')} yrs",
        "Matched Skills":len(d.get("matched_skills", [])),
        "Missing Skills":len(d.get("missing_skills", [])),
    })

if table_rows:
    df = pd.DataFrame(table_rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Match %": st.column_config.ProgressColumn(
                "Match %", min_value=0, max_value=100, format="%d%%"
            ),
        },
    )

st.markdown("---")

# ── Detailed Candidate Cards ──────────────────────────────────────────────────
st.subheader("🗂️ Detailed Candidate Reports")

for rank, (fname, res) in enumerate(successful, 1):
    d = res["data"]
    pct    = d.get("match_percentage", "?")
    status = d.get("candidate_status", "")
    icon   = medals[rank-1] if rank <= 3 else f"#{rank}"
    sc     = STATUS_COLOR.get(status, "⚪")

    with st.expander(
        f"{icon}  {d.get('candidate_name', fname)}  ·  {sc} {status}  ·  {pct}% match",
        expanded=(rank == 1),
    ):
        # Header row
        col_status, col_metrics = st.columns([2, 3])

        with col_status:
            st.markdown(STATUS_MD.get(status, f"### {status}"))
            st.markdown(f"**Department Fit:** `{d.get('department_fit','—')}`")
            st.markdown(f"**Education:** {d.get('education') or '—'}")
            certs = d.get("certifications", [])
            if certs:
                st.markdown(f"**Certifications:** {', '.join(certs)}")

        with col_metrics:
            m1, m2, m3 = st.columns(3)
            m1.metric("Match Score", f"{pct}%")
            m2.metric("Experience",  f"{d.get('experience','?')} yrs")
            m3.metric("Skills Hit",  f"{len(d.get('matched_skills',[]))}/{len(d.get('matched_skills',[])) + len(d.get('missing_skills',[]))}")

            # Score breakdown bars
            sb = d.get("score_breakdown", {})
            if sb:
                st.markdown("**Score Breakdown** *(Skills 40% · Experience 30% · Dept 20% · Certs 10%)*")
                breakdown_col = st.columns(4)
                labels = [("Skills", "skills_score"), ("Exp", "experience_score"),
                          ("Dept", "department_score"), ("Certs", "certification_score")]
                for col, (lbl, key) in zip(breakdown_col, labels):
                    v = sb.get(key, 0)
                    col.metric(lbl, f"{v}%")

        st.divider()

        # Skills
        sk1, sk2 = st.columns(2)
        with sk1:
            matched = d.get("matched_skills", [])
            st.markdown("**✅ Matched Skills**")
            st.markdown(chips(matched, "skill-chip") if matched else "—",
                        unsafe_allow_html=True)
        with sk2:
            missing = d.get("missing_skills", [])
            st.markdown("**❌ Missing Skills**")
            st.markdown(chips(missing, "miss-chip") if missing else "—",
                        unsafe_allow_html=True)

        st.divider()

        # Strengths & Weaknesses
        sw1, sw2 = st.columns(2)
        with sw1:
            st.markdown("**💪 Strengths**")
            for s in d.get("strengths", []):
                st.markdown(f"  • {s}")
        with sw2:
            st.markdown("**⚠️ Weaknesses**")
            for w in d.get("weaknesses", []):
                st.markdown(f"  • {w}")

        st.divider()

        # Reason & Recommendation
        st.markdown("**📝 Evaluation**")
        st.write(d.get("reason", "—"))
        rec = d.get("recommendation", "")
        if rec:
            st.info(f"💡 **Recruiter Recommendation:** {rec}")

        # Debug toggle
        if st.checkbox("Show raw API response", key=f"dbg_{rank}_{fname}", value=False):
            st.json(d)

# ── Error section ──────────────────────────────────────────────────────────────
if failed:
    st.markdown("---")
    st.subheader("⚠️ Processing Errors")
    for fname, res in failed:
        with st.expander(f"❌ {fname}"):
            st.error(res["message"])
