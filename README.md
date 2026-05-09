# Intelligent Recruitment and Workforce Screening System

## Overview

Intelligent Recruitment and Workforce Screening System is an AI-powered recruitment platform designed mainly for textile and manufacturing industries to automate resume screening, candidate evaluation, and recruitment analysis.

The system helps HR teams reduce manual screening effort by analyzing multiple resumes, comparing them against a Job Description (JD), generating candidate rankings, and producing recruiter-friendly reports.

The project supports both IT and non-IT roles, while giving primary focus to textile and manufacturing recruitment workflows.

---

# Features

## Job Description Upload

* Upload JD files in PDF, TXT, or DOCX format
* Extract:

  * Department
  * Job Role
  * Required Skills
  * Experience Requirements

## Multi-Resume Analysis

* Upload and analyze multiple resumes simultaneously
* Supports large-batch resume screening
* Independent processing for every resume

## AI-Powered Candidate Evaluation

* Resume parsing using AI
* Department classification
* Skill extraction
* Candidate suitability analysis
* Recruiter feedback generation

## Deterministic Scoring System

Instead of relying on random AI-generated scores, the system calculates scores using weighted criteria.

### Scoring Weights

| Criteria         | Weight |
| ---------------- | ------ |
| Skill Match      | 40%    |
| Experience Match | 30%    |
| JD Keyword Match | 20%    |
| Certifications   | 10%    |

### Final Score Formula

```text
Final Score =
(Skill Match × 0.4) +
(Experience Match × 0.3) +
(JD Keyword Match × 0.2) +
(Certification Match × 0.1)
```

## Candidate Ranking

* Automatic ranking based on final score
* Top 3 candidate selection
* Selected / Moderate Fit / Rejected classification

## Recruiter Dashboard

* Modern dark-themed Streamlit dashboard
* Candidate cards
* Recruitment statistics
* Match percentage visualization
* Department-wise analysis

## PDF Report Generation

* Download recruitment analysis reports in PDF format
* Includes:

  * JD summary
  * Candidate comparison table
  * Detailed candidate feedback
  * Top 3 candidates
  * Recruitment statistics

---

# Industry Focus

This project is mainly designed for:

* Textile Industries
* Garment Manufacturing Companies
* Manufacturing Industries
* HR Recruitment Teams

Supported departments include:

* HR
* Production
* Quality
* Merchandising
* Operations
* Accounts
* Logistics
* IT
* Non-IT Roles

---

# Technology Stack

## Frontend

* Streamlit

## Backend & Logic

* Python

## AI Integration

* Groq API
* Llama Models

## NLP & Processing

* PDF text extraction
* Resume parsing
* Keyword matching
* AI evaluation prompts

## PDF Generation

* ReportLab

---

# Project Workflow

```text
1. Upload Job Description
        ↓
2. Extract JD Requirements
        ↓
3. Upload Multiple Resumes
        ↓
4. Resume Parsing & Skill Extraction
        ↓
5. Candidate Evaluation
        ↓
6. Score Calculation
        ↓
7. Candidate Ranking
        ↓
8. Top 3 Candidate Selection
        ↓
9. PDF Report Generation
```

---

# Folder Structure

```text
project/
│
├── app/
│   ├── agents/
│   ├── prompts/
│   ├── services/
│   ├── utils/
│   └── main.py
│
├── ui/
│   ├── app.py
│   └── pdf_report.py
│
├── uploads/
├── assets/
├── requirements.txt
├── .env
└── README.md
```

---

# Installation

## Clone Repository

```bash
git clone <repository-url>
cd project-folder
```

## Create Virtual Environment

```bash
python -m venv venv
```

## Activate Virtual Environment

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_api_key_here
```

---

# Run the Application

```bash
streamlit run ui/app.py
```

---

# Usage

## Step 1

Upload Job Description

## Step 2

Upload one or multiple resumes

## Step 3

Click “Analyze Resumes”

## Step 4

View:

* Candidate scores
* Match percentages
* Recommendations
* Top 3 candidates

## Step 5

Download Recruitment Report PDF

---

# Example Output

## Candidate Evaluation

```json
{
  "candidate_name": "Ravi Kumar",
  "department_fit": "HR",
  "match_percentage": 88,
  "candidate_status": "Selected",
  "strengths": [
    "Strong recruitment experience",
    "Payroll and compliance knowledge"
  ],
  "weaknesses": [
    "Limited audit exposure"
  ],
  "recommendation": "Strong fit for HR Executive role in textile manufacturing industry."
}
```

---

# Challenges Faced

* Streamlit rerun issues causing repeated API calls
* AI quota limitations
* Multi-resume processing stability
* Duplicate candidate data handling
* Candidate isolation and state management
* Building deterministic scoring instead of random AI scoring
* PDF report generation consistency

---

# Future Enhancements

* Database integration
* Recruiter authentication system
* Resume history tracking
* Interview scheduling
* Email notifications
* Analytics dashboard
* Cloud deployment
* Employee onboarding module
* ERP integration

---

# Key Highlights

* AI-powered recruitment workflow
* Textile/manufacturing-focused recruitment system
* Multi-resume analysis
* Dynamic JD comparison
* Deterministic scoring engine
* Top 3 candidate ranking
* PDF report export
* Modern recruiter dashboard

---

# Author

Abinesh G

---
