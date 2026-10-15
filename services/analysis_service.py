import json

def generate_personalized_plan(scores_dict: dict, role: str) -> list:
    """
    Identifies the lowest-scoring dimensions from an interview evaluation,
    prioritizes the weak areas, and generates actionable, structured preparation
    plans with role-specific practice drills.
    """
    # Dimensions: communication_score, clarity_score, relevance_score, fluency_score, technical_score
    dimensions = [
        ("technical_score", "Technical Knowledge & Domain Depth", "High"),
        ("clarity_score", "Clarity & Structure", "High"),
        ("communication_score", "Communication Quality & Storytelling", "Medium"),
        ("fluency_score", "Fluency & Speech Pacing", "Medium"),
        ("relevance_score", "Answer Relevance & Prompt Alignment", "Low")
    ]

    # Sort dimensions by score ascending (lowest score first)
    sorted_dims = sorted(dimensions, key=lambda d: float(scores_dict.get(d[0], 75)))
    
    # Take the top 2 lowest areas (or any below 75)
    plans = []
    
    for key, name, default_priority in sorted_dims[:2]:
        val = round(float(scores_dict.get(key, 70)))
        
        if key == "technical_score":
            rec = f"Review foundational architectures and design trade-offs relevant to {role}. Focus on explaining data flow and edge cases."
            ai_focus = "Deep-dive into architectural trade-offs, scalability, and concrete system constraints."
            questions = [
                f"How would you explain the internal architecture of your core framework for {role} to a senior engineer?",
                "What strategies do you adopt to debug high-latency queries or bottlenecks in production?",
                "Explain the trade-offs between consistency and availability in distributed storage systems."
            ]
        elif key == "clarity_score":
            rec = "Structure every response into 3 distinct sections: 1. Core thesis/definition, 2. Implementation details, 3. Measurable outcome."
            ai_focus = "Structure answers using the STAR method: Situation, Task, Action, Result. Keep sentences under 25 words."
            questions = [
                "Tell me about a difficult bug or architectural problem you solved using the STAR method.",
                "Describe the high-level architecture of your most recent software project in 3 concise bullet points.",
                "How do you prioritize code readability versus rapid prototyping when developing a new feature?"
            ]
        elif key == "communication_score":
            rec = "Adopt the STAR framework (Situation, Task, Action, Result) to narrate past experiences with concrete ownership."
            ai_focus = "Emphasize personal ownership ('I implemented' rather than 'we did') and highlight measurable impact."
            questions = [
                "Tell me about a time you handled disagreement regarding technical design with a peer.",
                "Describe how you break down an ambiguous requirement into deliverable milestones.",
                "Give an example of a situation where you had to quickly learn a new technology stack to meet a deadline."
            ]
        elif key == "fluency_score":
            rec = "Complete 3 timed 90-second voice drills. Replace verbal fillers ('um', 'uh', 'like') with deliberate 1-second pauses."
            ai_focus = "Pacing control: target 120-140 words per minute with purposeful pauses."
            questions = [
                "Walk me through your resume and educational journey in under 90 seconds without rushing.",
                "What is a recent technology or framework that excited you, and why?",
                "Explain how you prioritize urgent production issues under time pressure."
            ]
        else: # relevance_score
            rec = "Directly mirror the interviewer's question in your opening sentence before elaborating on context."
            ai_focus = "Anchor the opening statement directly to the primary prompt topic before expanding into secondary details."
            questions = [
                "What is the single most important consideration when designing an API endpoint?",
                "How do you define software quality and how do you measure it in your projects?",
                "Why are you specifically interested in this job role at this stage of your career?"
            ]

        priority = "High" if val < 65 else ("Medium" if val < 75 else "Low")
        plans.append({
            "weak_area": f"{name} ({val}%)",
            "score": val,
            "recommendation": rec,
            "practice_questions": questions,
            "ai_focus": ai_focus,
            "priority": priority
        })

    return plans

def compare_interview_attempts(attempt_1: dict, attempt_2: dict) -> dict:
    """
    Compares two interview attempts side-by-side, calculating exact score deltas,
    percentage point improvements, and qualitative progress summaries.
    """
    metrics = [
        ("overall_score", "Overall Score"),
        ("relevance_score", "Answer Relevance"),
        ("clarity_score", "Clarity & Structure"),
        ("communication_score", "Communication"),
        ("fluency_score", "Fluency & Pacing"),
        ("technical_score", "Technical Knowledge")
    ]

    metric_deltas = []
    total_delta = 0.0

    for key, label in metrics:
        v1 = round(float(attempt_1.get(key, 0) or 0), 1)
        v2 = round(float(attempt_2.get(key, 0) or 0), 1)
        diff = round(v2 - v1, 1)
        total_delta += diff

        metric_deltas.append({
            "key": key,
            "label": label,
            "attempt_1": v1,
            "attempt_2": v2,
            "delta": diff,
            "improved": diff >= 0
        })

    avg_overall_delta = round(float(attempt_2.get("overall_score", 0) or 0) - float(attempt_1.get("overall_score", 0) or 0), 1)

    if avg_overall_delta > 5:
        verdict = f"Substantial Improvement! Your overall score increased by {avg_overall_delta}% points across attempts."
    elif avg_overall_delta >= 0:
        verdict = f"Steady Progress: Overall score increased by {avg_overall_delta}% points with notable consistency."
    else:
        verdict = f"Slight Dip: Overall score changed by {avg_overall_delta}% points. Focus on identified weak areas in your practice plan."

    return {
        "metric_deltas": metric_deltas,
        "overall_delta": avg_overall_delta,
        "improved": avg_overall_delta >= 0,
        "verdict": verdict,
        "attempt_1_role": attempt_1.get("job_role", "Software Developer"),
        "attempt_2_role": attempt_2.get("job_role", "Software Developer"),
        "attempt_1_date": attempt_1.get("date", "Attempt 1"),
        "attempt_2_date": attempt_2.get("date", "Attempt 2")
    }
