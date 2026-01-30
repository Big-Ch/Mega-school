# -*- coding: utf-8 -*-
"""Схемы для structured output (используются LangChain + OpenAI)"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class TopicOutput(BaseModel):
    name: str = Field(description="Topic name")
    priority: int = Field(ge=1, description="Priority (1=highest)")
    questions_budget: int = Field(default=2, ge=1, description="Max questions")
    status: Literal["pending", "in_progress", "completed", "skipped"] = Field(default="pending")


class InterviewPlanOutput(BaseModel):
    position: str = Field(description="Target position")
    target_grade: str = Field(description="Target grade")
    topics: list[TopicOutput] = Field(description="Interview topics")
    total_questions_limit: int = Field(default=8, description="Max total questions")


class AnswerAnalysisOutput(BaseModel):
    quality: Literal["excellent", "good", "partial", "poor"] = Field(description="Answer quality")
    confidence_detected: float = Field(ge=0, le=1, description="Confidence level 0-1")
    completeness: float = Field(ge=0, le=1, description="Completeness 0-1")
    off_topic: bool = Field(default=False, description="Is off-topic")
    needs_fact_check: bool = Field(default=False, description="Needs fact check")
    suspicious_claims: list[str] = Field(default_factory=list, description="Claims to check")
    candidate_asked_question: bool = Field(default=False, description="Asked question")
    candidate_question: Optional[str] = Field(default=None, description="The question")
    reasoning: str = Field(description="Analysis reasoning")


class VerifiedFactOutput(BaseModel):
    claim: str = Field(description="Checked claim")
    confidence: float = Field(ge=0, le=1, description="Confidence")
    source: Optional[str] = Field(default=None, description="Source")
    verification_method: Literal["web_search", "llm_confident"] = Field(default="web_search")


class FalseFactOutput(BaseModel):
    claim: str = Field(description="False claim")
    confidence: float = Field(ge=0, le=1, description="Confidence")
    correct_info: str = Field(description="Correct info")
    source: Optional[str] = Field(default=None, description="Source")
    verification_method: Literal["web_search", "llm_confident"] = Field(default="web_search")


class UnverifiedFactOutput(BaseModel):
    claim: str = Field(description="Unverified claim")
    reason: Literal["web_search_unavailable", "no_source_found", "llm_uncertain"] = Field(description="Reason")
    llm_assessment: Literal["possibly_true", "possibly_false", "unknown"] = Field(default="unknown")
    note: str = Field(default="Не влияет на оценку")


class FactCheckOutput(BaseModel):
    verified_true: list[VerifiedFactOutput] = Field(default_factory=list, description="True facts")
    verified_false: list[FalseFactOutput] = Field(default_factory=list, description="False facts")
    unverified: list[UnverifiedFactOutput] = Field(default_factory=list, description="Unverified")


class SkillConfirmedOutput(BaseModel):
    skill: str = Field(description="Skill name")
    confidence: float = Field(ge=0, le=1, description="Confidence")
    evidence: list[str] = Field(default_factory=list, description="Evidence")


class SkillGapOutput(BaseModel):
    skill: str = Field(description="Skill")
    severity: Literal["low", "medium", "high"] = Field(description="Severity")
    failed_at: str = Field(description="Turn ID")


class SoftSkillsOutput(BaseModel):
    clarity: float = Field(ge=0, le=1, description="Clarity")
    honesty: float = Field(ge=0, le=1, description="Honesty")
    engagement: float = Field(ge=0, le=1, description="Engagement")


class EvaluationOutput(BaseModel):
    skills_confirmed: list[SkillConfirmedOutput] = Field(default_factory=list, description="Confirmed")
    skills_gaps: list[SkillGapOutput] = Field(default_factory=list, description="Gaps")
    soft_skills: SoftSkillsOutput = Field(description="Soft skills")
    hallucinations_detected: int = Field(default=0, ge=0, description="Hallucinations count")
    off_topic_attempts: int = Field(default=0, ge=0, description="Off-topic count")
    current_grade_estimate: Literal[
        "Junior", "Junior+", "Middle-", "Middle", "Middle+", "Senior-", "Senior"
    ] = Field(description="Grade estimate")
    grade_confidence: float = Field(ge=0, le=1, description="Confidence")
    reasoning: str = Field(default="", description="Reasoning")


class QuestionHandlerOutput(BaseModel):
    question_detected: str = Field(description="Detected question")
    response: str = Field(description="Response")
    return_to_interview: bool = Field(default=True)


class DecisionOutput(BaseModel):
    grade: Literal[
        "Junior", "Junior+", "Middle-", "Middle", "Middle+", "Senior-", "Senior"
    ] = Field(description="Grade")
    recommendation: Literal["Strong No Hire", "No Hire", "Hire", "Strong Hire"] = Field(description="Recommendation")
    confidence: float = Field(ge=0, le=1, description="Confidence")


class KnowledgeGapOutput(BaseModel):
    topic: str = Field(description="Topic")
    correct_answer: str = Field(description="Correct answer")


class TechnicalReviewOutput(BaseModel):
    confirmed_skills: list[str] = Field(default_factory=list, description="Skills")
    knowledge_gaps: list[KnowledgeGapOutput] = Field(default_factory=list, description="Gaps")


class RoadmapItemOutput(BaseModel):
    topic: str = Field(description="Topic")
    resources: list[str] = Field(default_factory=list, description="Resources")


class FinalFeedbackOutput(BaseModel):
    decision: DecisionOutput = Field(description="Decision")
    technical_review: TechnicalReviewOutput = Field(description="Technical review")
    soft_skills: SoftSkillsOutput = Field(description="Soft skills")
    roadmap: list[RoadmapItemOutput] = Field(default_factory=list, description="Roadmap")
