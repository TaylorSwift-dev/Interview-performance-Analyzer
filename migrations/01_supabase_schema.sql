-- Supabase PostgreSQL Migration for AI Interview Performance Analyzer
-- Conforms to Section 3 of project requirements:
-- Includes profiles, resumes, question_bank, interviews, interview_questions, answers, evaluations, practice_plans
-- Includes Row Level Security (RLS) policies, indexes, and foreign keys.

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- A. PROFILES
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    education TEXT,
    college_name TEXT,
    experience_level TEXT DEFAULT 'Fresher',
    target_industry TEXT DEFAULT 'IT & Software',
    target_job_role TEXT DEFAULT 'Software Developer',
    technical_skills TEXT, -- JSON array of skills
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can insert their own profile"
    ON profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- B. RESUMES
CREATE TABLE IF NOT EXISTS resumes (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    file_storage_path TEXT NOT NULL,
    extracted_text TEXT,
    extracted_skills JSONB DEFAULT '[]'::jsonb,
    projects JSONB DEFAULT '[]'::jsonb,
    education_details TEXT,
    experience_details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own resumes"
    ON resumes FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own resumes"
    ON resumes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own resumes"
    ON resumes FOR DELETE
    USING (auth.uid() = user_id);

-- C. QUESTION_BANK (Student-owned & public)
CREATE TABLE IF NOT EXISTS question_bank (
    id BIGSERIAL PRIMARY KEY,
    owner_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- NULL = public system question
    question_text TEXT NOT NULL,
    category TEXT NOT NULL,
    topic TEXT NOT NULL,
    job_role TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'Medium', -- 'Easy', 'Medium', 'Hard'
    expected_answer_or_rubric TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qbank_owner ON question_bank(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_qbank_role ON question_bank(job_role);
CREATE INDEX IF NOT EXISTS idx_qbank_category ON question_bank(category);
ALTER TABLE question_bank ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read public questions or their own"
    ON question_bank FOR SELECT
    USING (is_public = TRUE OR auth.uid() = owner_user_id);

CREATE POLICY "Users can insert their own questions"
    ON question_bank FOR INSERT
    WITH CHECK (auth.uid() = owner_user_id);

CREATE POLICY "Users can update their own questions"
    ON question_bank FOR UPDATE
    USING (auth.uid() = owner_user_id);

CREATE POLICY "Users can delete their own questions"
    ON question_bank FOR DELETE
    USING (auth.uid() = owner_user_id);

-- D. INTERVIEWS
CREATE TABLE IF NOT EXISTS interviews (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Mock Interview Session',
    target_industry TEXT NOT NULL DEFAULT 'IT & Software',
    target_job_role TEXT NOT NULL DEFAULT 'Software Developer',
    interview_type TEXT NOT NULL DEFAULT 'Technical', -- 'Technical', 'HR', 'Role-based'
    difficulty TEXT NOT NULL DEFAULT 'Medium',
    total_questions INTEGER NOT NULL DEFAULT 4,
    status TEXT NOT NULL DEFAULT 'in_progress', -- 'in_progress', 'completed'
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    overall_score NUMERIC(5,2) DEFAULT 0.00
);

CREATE INDEX IF NOT EXISTS idx_interviews_user ON interviews(user_id);
ALTER TABLE interviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own interviews"
    ON interviews FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own interviews"
    ON interviews FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own interviews"
    ON interviews FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own interviews"
    ON interviews FOR DELETE
    USING (auth.uid() = user_id);

-- E. INTERVIEW_QUESTIONS
CREATE TABLE IF NOT EXISTS interview_questions (
    id BIGSERIAL PRIMARY KEY,
    interview_id BIGINT NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    question_bank_id BIGINT REFERENCES question_bank(id) ON DELETE SET NULL,
    question_text TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'Medium',
    question_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_iq_interview ON interview_questions(interview_id);
ALTER TABLE interview_questions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view questions in their interviews"
    ON interview_questions FOR SELECT
    USING (EXISTS (SELECT 1 FROM interviews i WHERE i.id = interview_questions.interview_id AND i.user_id = auth.uid()));

CREATE POLICY "Users can insert questions in their interviews"
    ON interview_questions FOR INSERT
    WITH CHECK (EXISTS (SELECT 1 FROM interviews i WHERE i.id = interview_questions.interview_id AND i.user_id = auth.uid()));

-- F. ANSWERS
CREATE TABLE IF NOT EXISTS answers (
    id BIGSERIAL PRIMARY KEY,
    interview_question_id BIGINT NOT NULL REFERENCES interview_questions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    answer_duration_seconds INTEGER,
    submitted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_answers_question ON answers(interview_question_id);
CREATE INDEX IF NOT EXISTS idx_answers_user ON answers(user_id);
ALTER TABLE answers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own answers"
    ON answers FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own answers"
    ON answers FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- G. EVALUATIONS
CREATE TABLE IF NOT EXISTS evaluations (
    id BIGSERIAL PRIMARY KEY,
    answer_id BIGINT NOT NULL UNIQUE REFERENCES answers(id) ON DELETE CASCADE,
    relevance_score NUMERIC(5,2) DEFAULT 0.00,
    clarity_score NUMERIC(5,2) DEFAULT 0.00,
    communication_score NUMERIC(5,2) DEFAULT 0.00,
    technical_score NUMERIC(5,2) DEFAULT 0.00,
    overall_score NUMERIC(5,2) DEFAULT 0.00,
    strengths JSONB DEFAULT '[]'::jsonb,
    weaknesses JSONB DEFAULT '[]'::jsonb,
    detailed_feedback TEXT,
    improvement_suggestion TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_answer ON evaluations(answer_id);
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their evaluations"
    ON evaluations FOR SELECT
    USING (EXISTS (SELECT 1 FROM answers a WHERE a.id = evaluations.answer_id AND a.user_id = auth.uid()));

CREATE POLICY "Users can insert their evaluations"
    ON evaluations FOR INSERT
    WITH CHECK (EXISTS (SELECT 1 FROM answers a WHERE a.id = evaluations.answer_id AND a.user_id = auth.uid()));

-- H. PRACTICE_PLANS
CREATE TABLE IF NOT EXISTS practice_plans (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    interview_id BIGINT REFERENCES interviews(id) ON DELETE SET NULL,
    weak_area TEXT NOT NULL,
    recommended_activity TEXT NOT NULL,
    practice_questions JSONB DEFAULT '[]'::jsonb,
    priority TEXT DEFAULT 'Medium', -- 'High', 'Medium', 'Low'
    status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed'
    due_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pp_user ON practice_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_pp_interview ON practice_plans(interview_id);
ALTER TABLE practice_plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their practice plans"
    ON practice_plans FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their practice plans"
    ON practice_plans FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their practice plans"
    ON practice_plans FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their practice plans"
    ON practice_plans FOR DELETE
    USING (auth.uid() = user_id);
