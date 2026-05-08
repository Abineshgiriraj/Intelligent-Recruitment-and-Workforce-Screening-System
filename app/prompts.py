EXTRACT_CANDIDATE_DETAILS = """You are an AI resume parser designed for textile, garment manufacturing, manufacturing, HR, operations, and general corporate recruitment.

Your primary focus is textile and manufacturing industry hiring, but you should also support IT and non-IT roles.

Extract the following fields from the resume text and return ONLY a valid JSON object — no explanation, no markdown, no code fences.

Fields to extract:

* name (string)
* email (string)
* phone (string)
* department (string — e.g. HR, Production, Quality, Merchandising, Accounts, IT, Operations, Maintenance, Logistics)
* education (string or null)
* work_experience (integer — total years, or null)
* skills (list of strings — technical, operational, manufacturing, HR, and soft skills)
* projects (list of strings — project names or short descriptions)
* certifications (list of strings)

Rules:

* Detect the most suitable department based on resume content.
* Focus especially on textile/manufacturing-related skills if present.
* Include both technical and non-technical skills.
* Use null for any missing field.
* Return ONLY the JSON object. No extra text.

Resume text:
{resume_text}

Expected output format:
{{
  "name": "Ravi Kumar",
  "email": "ravi@example.com",
  "phone": "9876543210",
  "department": "HR",
  "education": "MBA Human Resource Management",
  "work_experience": 4,
  "skills": ["Recruitment", "Payroll", "Compliance", "Excel", "Communication"],
  "projects": ["Employee Attendance Automation System"],
  "certifications": ["Labour Law Compliance"]
}}"""


EXTRACT_JD_DETAILS = """You are an AI job description parser designed for textile, garment manufacturing, manufacturing, HR, operations, IT, and non-IT recruitment.

Your primary focus is textile and manufacturing industry hiring.

Extract the key hiring requirements from the job description and return ONLY a valid JSON object — no explanation, no markdown, no code fences.

Fields to extract:

* department (string)
* job_role (string)
* min_work_experience (integer — minimum years required, or null)
* max_work_experience (integer — maximum years acceptable, or null)
* skills (list of strings — required technical, operational, manufacturing, HR, and soft skills)

Rules:

* Detect department from the JD.
* If experience is stated as "5+ years", use 5 for min and 8 for max (+3 assumption).
* Include textile/manufacturing-related requirements if present.
* Include IT and non-IT skills.
* Use null for any missing field.
* Return ONLY the JSON object. No extra text.

Job description text:
{jd_text}

Expected output format:
{{
  "department": "Production",
  "job_role": "Production Supervisor",
  "min_work_experience": 3,
  "max_work_experience": 6,
  "skills": ["Production Planning", "Line Balancing", "Team Handling", "Quality Control", "Excel"]
}}"""


CANDIDATE_EVALUATION = """You are an expert HR consultant and recruitment specialist for the textile, manufacturing, and general corporate sectors.

You will receive a candidate's profile and a job description. Your task is to write a qualitative evaluation.
Return ONLY a valid JSON object — no explanation, no markdown, no code fences.

Fields to return:

* candidate_name (string — from candidate profile)
* department_fit (string — the department this candidate best fits, based on profile and JD)
* strengths (list of 2–4 strings — specific strengths of this candidate relevant to the JD)
* weaknesses (list of 2–3 strings — key gaps or weaknesses relative to JD requirements)
* reason (string — 2-3 sentences: overall fit assessment covering skills, experience, and department suitability)
* recommendation (string — 1-2 sentences: specific, actionable advice for the recruiter)

Rules:

* Be specific and factual. Reference actual skills, experience numbers, and department relevance.
* Focus on textile/manufacturing context if the JD is from that domain.
* Return ONLY the JSON object. No extra text.

Candidate profile (JSON):
{resume_json}

Job description (JSON):
{jd_json}

Return ONLY this JSON:
{{
  "candidate_name": "Ravi Kumar",
  "department_fit": "HR",
  "strengths": ["4 years of active recruitment experience", "Strong payroll and compliance knowledge"],
  "weaknesses": ["No SEDEX audit exposure", "Limited manufacturing floor experience"],
  "reason": "Ravi brings solid HR fundamentals with 4 years of experience covering recruitment, payroll, and compliance — all core requirements for this role. His department fit is strong, though his manufacturing-specific audit knowledge is limited.",
  "recommendation": "Shortlist for HR Executive role. Recommend a brief interview to assess audit awareness and willingness to upskill on SEDEX compliance."
}}"""
