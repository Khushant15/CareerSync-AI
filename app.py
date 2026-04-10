from flask import Flask, render_template, request, redirect, url_for
import os

import pdfplumber
import docx
import re
from groq import Groq
from config import GROQ_API_KEY
from src.engines.tfidf_engine import TFIDFEngine
from src.engines.skill_engine import SkillEngine

app = Flask(__name__)

# Initialize ML Engines
tfidf_engine = TFIDFEngine()
skill_engine = SkillEngine()

# ------------------ EXTENDED ROLE SKILLS ------------------
ROLE_SKILLS = {
    "frontend": {
        "technical": ["html", "css", "javascript", "react", "vue", "next.js", "typescript", "tailwind", "sass", "redux", "jest"],
        "soft_skills": ["communication", "teamwork", "problem solving", "creativity", "attention to detail"],
        "tools": ["git", "vscode", "figma", "npm", "webpack", "vivid", "chrome devtools"]
    },
    "backend": {
        "technical": ["python", "java", "node.js", "django", "flask", "sql", "postgresql", "mongodb", "rest api", "graphql", "redis", "grpc"],
        "soft_skills": ["analytical thinking", "problem solving", "scalability mindset", "system design"],
        "tools": ["docker", "kubernetes", "aws", "git", "postman", "nginx", "jenkins"]
    },
    "fullstack": {
        "technical": ["html", "css", "javascript", "react", "node.js", "python", "sql", "typescript", "express", "mongodb", "next.js"],
        "soft_skills": ["leadership", "communication", "adaptability", "project management", "critical thinking"],
        "tools": ["git", "docker", "aws", "npm", "jenkins", "jira", "github actions"]
    },
    "data": {
        "technical": ["python", "r", "sql", "pandas", "numpy", "matplotlib", "seaborn", "scikit-learn", "statistics", "data mining", "pyspark"],
        "soft_skills": ["critical thinking", "data storytelling", "attention to detail", "domain knowledge"],
        "tools": ["jupyter", "tableau", "power bi", "excel", "spark", "hadoop", "airflow"]
    },
    "ml": {
        "technical": ["python", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "deep learning", "nlp", "computer vision", "transformers"],
        "soft_skills": ["research oriented", "mathematical modeling", "innovation", "persistence"],
        "tools": ["git", "cuda", "keras", "opencv", "mlflow", "databricks", "wandb"]
    }
}

# ------------------ AI ANALYSIS LOGIC (GROQ ONLY) ------------------
def get_ai_insights(resume_text, role, jd_text):
    prompt = f"""
    You are an expert career coach and ATS optimization specialist.
    Analyze the following resume for the role of {role}. 
    Job Description: {jd_text if jd_text else 'N/A'}
    
    Resume Content:
    {resume_text}
    
    Provide your analysis in the following STRICT format. Do not use markdown headers (like # or ##). Use only these labels:
    SUMMARY: [A 2-3 sentence professional pitch]
    SUGGESTIONS: [A bulleted list of 3 specific improvements]
    QUESTIONS: [A bulleted list of 4 interview questions (2 technical, 2 behavioral)]
    COVER_LETTER: [A concise, professional cover letter draft tailored to the role]
    """

    if GROQ_API_KEY:
        try:
            print(f"DEBUG: Attempting analysis with GROQ...")
            client = Groq(api_key=GROQ_API_KEY)
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            text = chat_completion.choices[0].message.content
            return parse_ai_response(text)
        except Exception as e:
            print(f"DEBUG: GROQ CRITICAL ERROR: {e}")
            return {
                "summary": f"AI Analysis failed: {str(e)}",
                "suggestions": ["Check your Groq API console for service status."],
                "questions": ["Is your API key active and has credit?"],
                "cover_letter": "Unable to generate due to API error."
            }

    return {
        "summary": "AI Analysis failed. Check API key.",
        "suggestions": ["Ensure your resume content is standard professional text."],
        "questions": ["What are your key achievements?"],
        "cover_letter": "AI is currently unable to generate a letter."
    }

def parse_ai_response(text):
    # More robust regex to handle markdown bolding, headers, and varied whitespace
    def extract_section(section_name, next_sections):
        pattern = rf"(?:#*|\**)\s*{section_name}\s*(?::|-|\**)\s*(.*?)(?=\n\s*(?:#*|\**)\s*(?:{'|'.join(next_sections)})\s*(?::|-|\**)|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    sections = ["SUMMARY", "SUGGESTIONS", "QUESTIONS", "COVER_LETTER"]
    
    res = {
        "summary": extract_section("SUMMARY", sections[1:]),
        "suggestions": extract_section("SUGGESTIONS", sections[2:] + ["SUMMARY"]),
        "questions": extract_section("QUESTIONS", sections[3:] + ["SUMMARY", "SUGGESTIONS"]),
        "cover_letter": extract_section("COVER_LETTER", ["SUMMARY", "SUGGESTIONS", "QUESTIONS"])
    }
    
    # Process bullet points for suggestions and questions
    if res["suggestions"]:
        res["suggestions"] = [s.strip().lstrip('- ').lstrip('* ').lstrip('1. ') for s in res["suggestions"].split('\n') if s.strip()]
    else:
        res["suggestions"] = []
        
    if res["questions"]:
        res["questions"] = [q.strip().lstrip('- ').lstrip('* ').lstrip('1. ') for q in res["questions"].split('\n') if q.strip()]
    else:
        res["questions"] = []

    # Final defaults if extraction failed
    return {
        "summary": res["summary"] or "AI could not generate summary in expected format.",
        "suggestions": res["suggestions"],
        "questions": res["questions"],
        "cover_letter": res["cover_letter"] or "AI could not generate cover letter in expected format."
    }

# ------------------ HELPERS ------------------
def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s@\.\+]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_text(file):
    text = ""
    try:
        if file.filename.endswith(".pdf"):
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    content = page.extract_text()
                    if content: text += content + "\n"
        elif file.filename.endswith(".docx"):
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
    except Exception as e:
        print(f"CRITICAL Extraction Error: {e}")
    if not text.strip():
        print("WARNING: No text extracted.")
    return text.strip()

def extract_contact_info(text):
    email = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    phone = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    linkedin = re.search(r"linkedin\.com/in/[\w\-]+", text)
    return {
        "email": email.group(0) if email else "Not found",
        "phone": phone.group(0) if phone else "Not found",
        "linkedin": linkedin.group(0) if linkedin else "Not found"
    }

def analyze_skills_ml(raw_text):
    # Use the advanced SkillEngine for data-driven results
    skill_results = skill_engine.analyze_resume(raw_text)
    avg_skill_score = sum(skill_results["scores"].values()) / len(skill_results["scores"])
    return skill_results, round(avg_skill_score, 2)

def ats_score(resume_text, file_type):
    score = 100
    warnings = []
    bad_icons = ["★", "●", "→", "■", "♦", "✔", "✅"]
    if any(icon in resume_text for icon in bad_icons):
        score -= 10
        warnings.append("Avoid complex icons.")
    if "table" in resume_text.lower():
        score -= 10
        warnings.append("Tables detected.")
    if len(resume_text.split()) < 300:
        score -= 15
        warnings.append("Content volume is low.")
    return max(score, 0), warnings

# ------------------ ROUTES ------------------

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", score=None)

@app.route("/analyze", methods=["POST"])
def analyze():
    resume = request.files.get("resume")
    role = request.form.get("job_role")
    jd = request.form.get("jd", "")

    if not resume or not role:
        return redirect(url_for("index"))

    raw_text = extract_text(resume)
    if not raw_text:
        return render_template("index.html", score=None, error="Could not extract text.")
        
    contact_info = extract_contact_info(raw_text)
    skill_analysis, avg_skill_score = analyze_skills_ml(raw_text)
    ats, ats_warnings = ats_score(raw_text, resume.filename.split(".")[-1])
    
    # ML Engine Analysis (TF-IDF)
    ml_results = tfidf_engine.analyze(raw_text, jd)
    
    # Real AI Insights (Groq Only)
    ai_insights = get_ai_insights(raw_text, role, jd)

    return render_template(
        "index.html",
        score=avg_skill_score,
        contact=contact_info,
        skill_analysis=skill_analysis,
        ats_score=ats,
        ats_warnings=ats_warnings,
        ml=ml_results,  # Traditional ML results
        ai=ai_insights  # LLM results
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
