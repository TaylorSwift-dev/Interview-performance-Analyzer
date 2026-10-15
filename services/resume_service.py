import re
import os
from pypdf import PdfReader

# Standard comprehensive skills vocabulary
TECH_SKILLS_DICTIONARY = [
    "Python", "Java", "C++", "C", "C#", "JavaScript", "TypeScript", "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin",
    "Flask", "Django", "FastAPI", "React", "React.js", "Angular", "Vue", "Vue.js", "Node.js", "Express", "Spring Boot",
    "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Cassandra", "Elasticsearch",
    "HTML", "HTML5", "CSS", "CSS3", "Bootstrap", "Tailwind CSS", "REST API", "GraphQL", "WebSockets",
    "Git", "GitHub", "GitLab", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux", "CI/CD", "Jenkins",
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Scikit-Learn", "Pandas", "NumPy", "NLP", "OpenCV",
    "Data Analysis", "Data Structures", "Algorithms", "Object-Oriented Programming", "OOP", "System Design",
    "Cybersecurity", "Network Security", "Cryptography", "Penetration Testing", "Wireshark"
]

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract readable plain text from uploaded PDF file using pypdf.
    Handles exceptions and empty files safely.
    """
    if not os.path.exists(pdf_path):
        return ""
    
    extracted_text = []
    try:
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text.append(text)
    except Exception as e:
        print(f"Error parsing PDF {pdf_path}: {e}")
        return ""

    combined_text = "\n".join(extracted_text).strip()
    return combined_text

def analyze_resume_text(text: str) -> dict:
    """
    Analyzes resume text to identify skills, projects, education, and experience.
    Uses regex pattern recognition and dictionary lookups.
    """
    if not text:
        return {
            "skills": [],
            "projects": [],
            "education": "Not detected",
            "experience": "Fresher / Student",
            "extracted_length": 0
        }

    lower_text = text.lower()
    
    # 1. Identify Technical Skills
    found_skills = []
    for skill in TECH_SKILLS_DICTIONARY:
        # Match as whole word / boundary
        pattern = r'(?i)\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text):
            if skill not in found_skills:
                found_skills.append(skill)

    # 2. Identify Projects
    projects = []
    # Search for project section or numbered project patterns
    project_lines = []
    in_project_section = False
    
    for line in text.split("\n"):
        clean_line = line.strip()
        if not clean_line:
            continue
        
        # Check section boundaries
        if re.search(r'^(?:projects?|academic projects?|key projects?):?', clean_line, re.IGNORECASE):
            in_project_section = True
            continue
        elif in_project_section and re.search(r'^(?:education|skills?|experience|certifications?|awards?):?', clean_line, re.IGNORECASE):
            in_project_section = False

        if in_project_section:
            if clean_line.startswith(('-', '•', '*', '1.', '2.', '3.', '4.', '5.')):
                project_lines.append(clean_line.lstrip('-•* 1234567890.').strip())
            elif len(clean_line) > 15 and len(clean_line) < 120 and ":" in clean_line:
                project_lines.append(clean_line)

    if project_lines:
        projects = project_lines[:5]
    else:
        # Fallback heuristic: look for lines mentioning Built, Developed, Created, Implemented
        for line in text.split("\n"):
            clean_line = line.strip()
            if re.search(r'\b(developed|built|implemented|created|designed)\b', clean_line, re.IGNORECASE) and len(clean_line) > 20:
                projects.append(clean_line[:120])
                if len(projects) >= 3:
                    break

    # 3. Identify Education
    education = "Not detected"
    edu_matches = []
    if re.search(r'\b(b\.?tech|bachelor of technology|b\.?e\.?|bca|mca|b\.?sc|m\.?tech|master)\b', lower_text):
        for line in text.split("\n"):
            if re.search(r'\b(b\.?tech|bachelor|b\.?e\.?|bca|mca|degree|college|university|institute)\b', line, re.IGNORECASE):
                edu_matches.append(line.strip())
        if edu_matches:
            education = " | ".join(edu_matches[:2])
    elif "university" in lower_text or "college" in lower_text:
        education = "University / College Degree"

    # 4. Identify Experience Level
    experience = "Fresher / Student"
    if re.search(r'\b(\d+\+?\s*(?:years?|yrs?)\s*(?:of\s*)?experience)\b', lower_text):
        match = re.search(r'(\d+\+?\s*(?:years?|yrs?)\s*(?:of\s*)?experience)', lower_text)
        if match:
            experience = match.group(1).title()
    elif re.search(r'\b(intern|internship|trainee)\b', lower_text):
        experience = "Internship Experience"
    elif re.search(r'\b(software engineer|developer|analyst|associate)\b', lower_text) and not re.search(r'\b(aspiring|seeking)\b', lower_text):
        experience = "Professional Experience"

    return {
        "skills": found_skills,
        "projects": projects,
        "education": education,
        "experience": experience,
        "extracted_length": len(text)
    }
