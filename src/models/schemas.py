# -*- coding: utf-8 -*-
"""Внутренние модели данных"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class CandidateProfile(BaseModel):
    name: str
    position: str
    target_grade: Literal["Junior", "Middle", "Senior"]
    experience: str


class TopicInfo(BaseModel):
    name: str
    priority: int = Field(ge=1)
    questions_budget: int = Field(default=2, ge=1)
    status: Literal["pending", "in_progress", "completed", "skipped"] = "pending"
    questions_asked: int = 0
    temperature: float = Field(default=0.5, ge=0, le=1)


class InterviewPlan(BaseModel):
    position: str
    target_grade: str
    topics: list[TopicInfo] = Field(default_factory=list)
    total_questions_limit: int = 8
    current_topic_index: int = 0


class AnswerAnalysis(BaseModel):
    quality: Literal["excellent", "good", "partial", "poor"]
    confidence_detected: float= Field(ge=0, le=1)
    completeness: float = Field(ge=0, le=1)
    off_topic: bool = False
    needs_fact_check: bool = False
    suspicious_claims: list[str] = Field(default_factory=list)
    candidate_asked_question: bool = False
    candidate_question: Optional[str] = None
    reasoning: str


class VerifiedFact(BaseModel):
    claim: str
    confidence: float = Field(ge=0, le=1)
    source: Optional[str] = None
    verification_method: Literal["web_search", "llm_confident"] = "web_search"


class FalseFact(BaseModel):
    claim: str
    confidence: float = Field(ge=0, le=1)
    correct_info: str
    source: Optional[str] = None
    verification_method: Literal["web_search", "llm_confident"] = "web_search"


class UnverifiedFact(BaseModel):
    claim: str
    reason: Literal["web_search_unavailable", "no_source_found", "llm_uncertain"]
    llm_assessment: Literal["possibly_true", "possibly_false", "unknown"] = "unknown"
    note: str = "Не влияет на оценку"


class FactCheckResult(BaseModel):
    verified_true: list[VerifiedFact] = Field(default_factory=list)
    verified_false: list[FalseFact] = Field(default_factory=list)
    unverified: list[UnverifiedFact] = Field(default_factory=list)


class SkillConfirmed(BaseModel):
    skill: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)


class SkillGap(BaseModel):
    skill: str
    severity: Literal["low", "medium", "high"]
    failed_at: str
    correct_answer: Optional[str] = None


class SoftSkills(BaseModel):
    clarity: float = Field(default=0.5, ge=0, le=1)
    honesty: float = Field(default=0.5, ge=0, le=1)
    engagement: float = Field(default=0.5, ge=0, le=1)


class EvaluationState(BaseModel):
    skills_confirmed: list[SkillConfirmed] = Field(default_factory=list)
    skills_gaps: list[SkillGap] = Field(default_factory=list)
    soft_skills: SoftSkills = Field(default_factory=SoftSkills)
    hallucinations_detected: int = 0
    off_topic_attempts: int = 0
    current_grade_estimate: Literal["Junior", "Junior+", "Middle-", "Middle", "Middle+", "Senior-", "Senior"] = "Junior"
    grade_confidence: float = Field(default=0.5, ge=0, le=1)
    confidence_history: list[float] = Field(default_factory=list)  # История уверенности по ходам


class RouterDecision(BaseModel):
    next_topic: Optional[str] = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    action: Literal["ask_question", "ask_followup", "give_hint", "change_topic", "end_interview"] = "ask_question"
    hint: Optional[str] = None
    reasoning: str = ""


class QuestionHandlerResponse(BaseModel):
    question_detected: str
    response: str
    return_to_interview: bool = True


class Decision(BaseModel):
    grade: Literal["Junior", "Junior+", "Middle-", "Middle", "Middle+", "Senior-", "Senior"]
    recommendation: Literal["Strong No Hire", "No Hire", "Hire", "Strong Hire"]
    confidence: float = Field(ge=0, le=1)


class KnowledgeGap(BaseModel):
    topic: str
    correct_answer: str


class RoadmapItem(BaseModel):
    topic: str
    resources: list[str] = Field(default_factory=list)



class TechnicalReview(BaseModel):
    confirmed_skills: list[str] = Field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)
    unverified_claims: list[UnverifiedFact] = Field(default_factory=list)


class FinalFeedback(BaseModel):
    decision: Decision
    technical_review: TechnicalReview
    soft_skills: SoftSkills
    roadmap: list[RoadmapItem] = Field(default_factory=list)
    confidence_trend: str = ""  # "↗ растёт", "↘ падает", "→ стабильно"


class Message(BaseModel):
    role: Literal["interviewer", "candidate"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class InternalThoughts(BaseModel):
    answer_analyzer: Optional[dict] = None
    fact_checker: Optional[dict] = None
    evaluator: Optional[dict] = None
    router: Optional[dict] = None
    question_handler: Optional[dict] = None


class TurnLog(BaseModel):
    turn_id: int
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    agent_visible_message: str
    user_message: Optional[str] = None
    internal_thoughts: InternalThoughts = Field(default_factory=InternalThoughts)
