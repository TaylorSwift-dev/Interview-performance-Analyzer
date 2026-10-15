import os
import json
import re
import random

# Attempt to load google-generativeai safely
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY and GENAI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Warning: Failed to configure Gemini API: {e}")

# Pre-defined curated question bank across roles and topics (Rule-based & fallback)
CURATED_QUESTIONS = {
    "Software Developer": {
        "Technical": [
            "Can you explain how indexing works in relational databases and what trade-offs it introduces?",
            "What is the difference between synchronous and asynchronous operations in web applications?",
            "Explain how the call stack and event loop operate in runtime environments.",
            "How would you design a scalable caching strategy for high-frequency database read queries?",
            "What are the core differences between monolithic architectures and microservices?",
            "Describe the concept of database transactions and the ACID properties with real-world examples."
        ],
        "HR": [
            "Tell me about a time you worked on a team project and had a disagreement about the technical direction. How did you resolve it?",
            "Describe a situation where a deadline was shortened or requirements changed unexpectedly. How did you adapt?",
            "What motivates you to pursue software engineering, and what technical areas are you most eager to master?",
            "Can you tell me about a time when you received constructive feedback on your code and how you incorporated it?"
        ],
        "Role-based": [
            "Walk me through your development workflow from receiving a user story to deploying code to production.",
            "How do you approach automated testing: what is your balance between unit, integration, and end-to-end tests?",
            "If an application suddenly exhibits high latency in production, what is your systematic troubleshooting process?"
        ]
    },
    "Web Developer": {
        "Technical": [
            "Explain the Virtual DOM and how modern frontend frameworks optimize UI rendering and minimize reflows.",
            "What is Cross-Origin Resource Sharing (CORS), and what backend headers are needed to resolve cross-origin issues securely?",
            "How do CSS Grid and Flexbox differ in responsive web layout design?",
            "What strategies do you use to improve web page load speed and Core Web Vitals?"
        ],
        "HR": [
            "How do you balance aesthetic design considerations with strict web accessibility (a11y) standards?",
            "Describe a time you collaborated closely with a UI/UX designer or product manager on a challenging feature."
        ],
        "Role-based": [
            "How do you ensure state management consistency across a complex Single Page Application (SPA)?",
            "What security measures do you implement to guard web applications against XSS and CSRF attacks?"
        ]
    },
    "Data Analyst": {
        "Technical": [
            "How do you systematically identify and handle missing values and outliers in a tabular dataset?",
            "Explain the difference between inner, outer, left, and cross joins in SQL, and when each is appropriate.",
            "What are common visualization pitfalls when communicating analytical insights to non-technical stakeholders?",
            "How do you measure correlation versus causation in observational data?"
        ],
        "HR": [
            "Describe a time when data contradicted a stakeholder's intuition. How did you present your findings?",
            "How do you prioritize multiple competing reporting and analytics requests under tight deadlines?"
        ],
        "Role-based": [
            "Walk me through an end-to-end data pipeline you built or analyzed, from raw ingestion to dashboard reporting."
        ]
    },
    "AI/ML Engineer": {
        "Technical": [
            "Explain the bias-variance tradeoff and how techniques like regularization and cross-validation address it.",
            "What is the difference between precision, recall, F1-score, and ROC-AUC? When is accuracy a deceptive metric?",
            "How do Transformer architectures utilize self-attention mechanisms compared to recurrent neural networks (RNNs)?",
            "What are the key considerations when fine-tuning a Large Language Model versus using Retrieval-Augmented Generation (RAG)?"
        ],
        "HR": [
            "How do you communicate complex machine learning model uncertainties and limitations to executive business leaders?",
            "Describe how you stay current with the fast-moving AI research and open-source landscape."
        ],
        "Role-based": [
            "How do you monitor and prevent concept drift and data drift once a machine learning model is deployed to production?"
        ]
    },
    "Cybersecurity Analyst": {
        "Technical": [
            "What is the difference between symmetric and asymmetric encryption, and how do they work together in TLS?",
            "Explain the Zero Trust security model and its core verification principles.",
            "How do you detect and mitigate SQL injection and privilege escalation vulnerabilities in a web stack?"
        ],
        "HR": [
            "How do you foster a security-first culture in an engineering team without creating friction for developers?",
            "Describe how you handle high-pressure security incident response protocols."
        ],
        "Role-based": [
            "Walk me through your methodology for conducting vulnerability assessments and risk scoring."
        ]
    }
}

def generate_question(industry: str, role: str, interview_type: str, difficulty: str,
                      resume_context: dict = None, previous_qa: list = None) -> str:
    """
    Generates a personalized, adaptive interview question using Gemini LLM if configured,
    or intelligent fallback using curated questions and candidate resume context.
    """
    resume_context = resume_context or {}
    previous_qa = previous_qa or []
    skills = resume_context.get("skills", [])
    projects = resume_context.get("projects", [])

    # If Gemini API key is configured, call Gemini
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key and GENAI_AVAILABLE:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            prev_prompt = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in previous_qa[-3:]])
            
            prompt = f"""You are an expert technical and HR interviewer conducting a professional mock interview.
Target Industry: {industry}
Job Role: {role}
Interview Type: {interview_type} (e.g. Technical, HR, Role-based)
Difficulty Level: {difficulty} (Easy, Medium, Hard)
Candidate Resume Technical Skills: {', '.join(skills[:8]) if skills else 'Not specified'}
Candidate Highlighted Projects: {'; '.join(projects[:3]) if projects else 'Not specified'}

Previous Q&A in this interview:
{prev_prompt if prev_prompt else 'None (This is Question 1).'}

Generate the next SINGLE interview question.
Rules:
1. Make it relevant to the candidate's target role and resume background.
2. If previous answers showed incomplete understanding or interesting project details, adapt naturally by asking an insightful follow-up.
3. Do NOT repeat previous questions.
4. Output ONLY the question text itself without preamble, numbering, or quotation marks.
"""
            response = model.generate_content(prompt)
            if response and response.text:
                cleaned = response.text.strip().strip('"').strip("'")
                if len(cleaned) > 15:
                    return cleaned
        except Exception as e:
            print(f"Gemini API generation failed, falling back to rule-based engine: {e}")

    # Fallback Adaptive / Resume-Aware Logic
    # 1. If Candidate has projects and this is Question 1, ask about their specific project
    if len(previous_qa) == 0 and projects:
        project_sample = projects[0]
        # Clean title
        clean_title = project_sample.split(":")[0] if ":" in project_sample else project_sample
        return f"I noticed you developed '{clean_title}'. Can you explain the system architecture, your individual role, and the most challenging technical hurdle you solved?"

    # 2. If Candidate has specific technical skills and it's Technical interview
    if len(previous_qa) == 1 and skills and interview_type == "Technical":
        skill_pick = skills[0]
        return f"Your resume highlights experience with {skill_pick}. How have you leveraged {skill_pick} in a recent project, and what are its key advantages and limitations?"

    # 3. Adaptive follow-up on previous answer
    if previous_qa:
        last_turn = previous_qa[-1]
        last_answer = last_turn.get("answer", "")
        last_q = last_turn.get("question", "")
        # If the last answer was quite short (< 30 words), ask for depth/tradeoffs
        if len(last_answer.split()) < 30:
            return f"Building on your last answer, could you dive deeper into the technical trade-offs and edge cases you would consider in a production environment?"
        # If last answer was strong and difficulty is Hard
        elif len(last_answer.split()) > 70 and difficulty == "Hard":
            return f"That's a thorough explanation. How would your proposed solution scale when handling millions of concurrent requests or gigabytes of streaming data?"

    # 4. Lookup from curated dictionary
    role_bucket = CURATED_QUESTIONS.get(role, CURATED_QUESTIONS.get("Software Developer"))
    type_bucket = role_bucket.get(interview_type, role_bucket.get("Technical", []))
    
    # Filter out already asked questions
    asked_texts = [item.get("question", "").lower() for item in previous_qa]
    unasked = [q for q in type_bucket if q.lower() not in asked_texts]

    if unasked:
        return unasked[0]
    
    # Generic fallback
    return f"Can you describe a challenging technical or system problem you recently solved, focusing on your specific decision-making process?"

def evaluate_answer(question: str, answer: str, role: str, interview_type: str, resume_context: dict = None) -> dict:
    """
    Evaluates an answer across 5 core dimensions:
    Relevance, Clarity, Communication, Fluency, Technical Knowledge.
    Returns structured scores, strengths, weaknesses, feedback, improvement suggestions, and score explanations.
    """
    resume_context = resume_context or {}
    clean_answer = (answer or "").strip()
    words = clean_answer.split()
    word_count = len(words)

    # If Gemini API key is configured, call Gemini for rich evaluation
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key and GENAI_AVAILABLE and word_count >= 5:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            eval_prompt = f"""You are a senior hiring manager and interview coach evaluating a candidate's interview response.

Role: {role}
Interview Type: {interview_type}
Question: {question}
Candidate Answer: {clean_answer}

Evaluate the response objectively on a scale of 0 to 100 for each dimension:
1. relevance_score (0-100): How directly does it address the question?
2. clarity_score (0-100): Is it logically structured, concise, and easy to understand?
3. communication_score (0-100): Professional tone, confidence, narrative flow, STAR method application.
4. fluency_score (0-100): Vocabulary, smooth phrasing, absence of fillers or disjointed thoughts.
5. technical_score (0-100): Depth, correctness, architectural and domain accuracy.

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "relevance_score": 85,
  "clarity_score": 80,
  "communication_score": 78,
  "fluency_score": 82,
  "technical_score": 75,
  "strengths": ["Clear explanation of X", "Good practical example"],
  "weaknesses": ["Missed discussing edge case Y", "Could be more structured"],
  "feedback": "Comprehensive constructive paragraph summarizing performance.",
  "improvement_suggestion": "One specific actionable drill for the next attempt.",
  "explain": {{
    "relevance": "Explanation of relevance score",
    "clarity": "Explanation of clarity score",
    "communication": "Explanation of communication score",
    "fluency": "Explanation of fluency score",
    "technical": "Explanation of technical score"
  }}
}}
"""
            response = model.generate_content(eval_prompt)
            if response and response.text:
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    # Sanitize scores
                    for k in ["relevance_score", "clarity_score", "communication_score", "fluency_score", "technical_score"]:
                        parsed[k] = max(10, min(100, float(parsed.get(k, 70))))
                    return parsed
        except Exception as e:
            print(f"Gemini evaluation failed, using rule-based evaluator: {e}")

    # Fallback Rule-Based Evaluator
    # Empty or very short answer
    if word_count < 8:
        return {
            "relevance_score": 30.0,
            "clarity_score": 35.0,
            "communication_score": 30.0,
            "fluency_score": 40.0,
            "technical_score": 25.0,
            "strengths": ["Attempted to provide an answer."],
            "weaknesses": [
                "Answer was extremely brief and lacked detail.",
                "Did not provide concrete examples or technical reasoning."
            ],
            "feedback": "Your response was too brief to demonstrate technical depth or communication clarity. Aim for at least 3-4 structured sentences explaining your reasoning.",
            "improvement_suggestion": "Practice expanding your answers using the STAR method: Situation, Task, Action, and Result.",
            "explain": {
                "relevance": "30% - Addressed the prompt superficially without elaboration.",
                "clarity": "35% - Too few words to assess structure.",
                "communication": "30% - Needs more professional articulation.",
                "fluency": "40% - Minimal vocabulary displayed.",
                "technical": "25% - Lacked technical details, algorithms, or architecture."
            }
        }

    # Keyword and structure analysis
    lower_ans = clean_answer.lower()
    
    # 1. Relevance: check overlap between question keywords and answer
    q_words = set(re.findall(r'\b\w{4,}\b', question.lower()))
    overlap = sum(1 for w in q_words if w in lower_ans)
    rel_score = 65.0 + min(30.0, overlap * 8.0)
    if word_count >= 30:
        rel_score = min(95.0, rel_score + 5)

    # 2. Clarity: sentence structure and punctuation
    sentences = [s for s in re.split(r'[.!?]+', clean_answer) if s.strip()]
    avg_sentence_len = word_count / max(1, len(sentences))
    clarity_score = 70.0
    if 10 <= avg_sentence_len <= 25:
        clarity_score += 15.0 # ideal sentence length
    elif avg_sentence_len > 35:
        clarity_score -= 10.0 # run-on sentences

    # 3. Communication & STAR indicators
    star_keywords = ["situation", "task", "action", "result", "because", "therefore", "implemented", "resolved", "impact", "metric"]
    star_matches = [w for w in star_keywords if w in lower_ans]
    comm_score = 65.0 + min(25.0, len(star_matches) * 6.0)

    # 4. Fluency & Filler words detection
    filler_words = ["um", "uh", "like", "you know", "sort of", "kind of", "basically", "actually"]
    filler_count = sum(len(re.findall(r'\b' + re.escape(fw) + r'\b', lower_ans)) for fw in filler_words)
    fluency_score = max(50.0, 85.0 - (filler_count * 5.0))
    if word_count > 60 and filler_count <= 1:
        fluency_score = min(95.0, fluency_score + 8.0)

    # 5. Technical score: technical vocabulary presence
    tech_keywords = [
        "index", "query", "database", "api", "async", "sync", "cache", "latency",
        "scale", "performance", "component", "state", "server", "architecture", "test",
        "security", "encryption", "model", "pipeline", "framework", "optimization", "algorithm"
    ]
    tech_matches = [w for w in tech_keywords if w in lower_ans]
    tech_score = 60.0 + min(35.0, len(tech_matches) * 7.0)

    # Strengths and Weaknesses synthesis
    strengths = []
    weaknesses = []

    if tech_matches:
        strengths.append(f"Demonstrated technical awareness by mentioning {', '.join(tech_matches[:3])}.")
    if len(star_matches) >= 2:
        strengths.append("Structured response with logical progression (action-oriented narrative).")
    if word_count >= 50:
        strengths.append("Provided detailed explanation with sufficient context.")
    if not strengths:
        strengths.append("Addressed the central premise of the question directly.")

    if filler_count >= 2:
        weaknesses.append(f"Detected {filler_count} filler phrase(s). Replace verbal pauses with silent 1-second pauses.")
    if len(tech_matches) == 0 and interview_type == "Technical":
        weaknesses.append("Lacked specific technical terminology or concrete framework examples.")
    if avg_sentence_len > 30:
        weaknesses.append("Several sentences were long and complex. Break down thoughts into concise points.")
    if len(weaknesses) == 0:
        weaknesses.append("Can further enhance answer with quantifiable performance metrics or trade-off analysis.")

    feedback = (
        f"Solid effort on this question. You demonstrated clear understanding of the topic with {word_count} words. "
        f"{'Your technical references were on point.' if tech_matches else 'Try to include more concrete implementation details next time.'} "
        f"{'Keep sentences concise for even crisper communication.' if avg_sentence_len > 25 else 'Pacing and sentence length were well-balanced.'}"
    )

    improvement = (
        f"In your next attempt, frame your answer with 3 clear components: "
        f"1) Direct answer/definition, 2) Real-world implementation details, and 3) Potential trade-offs or alternatives."
    )

    explain = {
        "relevance": f"{round(rel_score)}% - Directly addressed prompt keywords with clear contextual alignment.",
        "clarity": f"{round(clarity_score)}% - Sentence structure averaged {round(avg_sentence_len, 1)} words per sentence.",
        "communication": f"{round(comm_score)}% - Professional narrative tone with {len(star_matches)} structured transition cues.",
        "fluency": f"{round(fluency_score)}% - Fluid delivery with {filler_count} filler words detected.",
        "technical": f"{round(tech_score)}% - Incorporated {len(tech_matches)} relevant technical terms."
    }

    return {
        "relevance_score": round(rel_score, 1),
        "clarity_score": round(clarity_score, 1),
        "communication_score": round(comm_score, 1),
        "fluency_score": round(fluency_score, 1),
        "technical_score": round(tech_score, 1),
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "feedback": feedback,
        "improvement_suggestion": improvement,
        "explain": explain
    }
