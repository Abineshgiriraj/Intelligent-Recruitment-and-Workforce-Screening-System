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

Expected output format (do not include this line in output):
{{
"name": "Ravi Kumar",
"email": "[ravi@example.com](mailto:ravi@example.com)",
"phone": "9876543210",
"department": "HR",
"education": "MBA Human Resource Management",
"work_experience": 4,
"skills": [
"Recruitment",
"Payroll",
"Compliance",
"Excel",
"Communication"
],
"projects": [
"Employee Attendance Automation System"
],
"certifications": [
"Labour Law Compliance"
]
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

Expected output format (do not include this line in output):
{{
"department": "Production",
"job_role": "Production Supervisor",
"min_work_experience": 3,
"max_work_experience": 6,
"skills": [
"Production Planning",
"Line Balancing",
"Team Handling",
"Quality Control",
"Excel"
]
}}"""

CANDIDATE_EVALUATION = """You are an AI recruitment evaluation system designed mainly for textile and manufacturing industries, while also supporting IT and non-IT roles.

Evaluate the candidate against the job description and return ONLY a valid JSON object — no explanation, no markdown, no code fences.

Evaluation rules:

1. SKILLS:

* Check if the candidate matches the required skills from the JD.
* Consider technical, manufacturing, HR, operational, and soft skills.
* Treat related/equivalent skills as matches.
* Focus strongly on textile/manufacturing relevance if present.

2. EXPERIENCE:

* Candidate work_experience should reasonably match the JD requirements.
* Accept small variations in experience.

3. DEPARTMENT FIT:

* Determine whether the candidate is suitable for the department mentioned in the JD.

4. STATUS:

* Return "Selected" if the candidate is a strong or moderate fit.
* Return "Rejected" if the candidate lacks major required skills or experience.

Candidate profile (JSON):
{resume_json}

Job description requirements (JSON):
{jd_json}

Return ONLY this JSON (no extra text):

{{
"candidate_name": "Ravi Kumar",
"department_fit": "HR",
"candidate_status": "Selected or Rejected",
"reason": "Two or three sentences explaining the decision based on skills, experience, department suitability, and manufacturing relevance.",
"matched_skills": [
"Recruitment",
"Payroll",
"Compliance"
],
"missing_skills": [
"SEDEX Audit"
],
"skill_match_percentage": 82,
"experience": 4,
"recommendation": "Strong fit for HR Executive role in textile manufacturing industry."
}}"""
