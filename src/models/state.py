# -*- coding: utf-8 -*-
from typing import TypedDict, Annotated, Optional, Literal
from operator import add
from langgraph.graph.message import add_messages

from .schemas import (
    CandidateProfile,
    InterviewPlan,
    AnswerAnalysis,
    FactCheckResult,
    EvaluationState,
    RouterDecision,
    FinalFeedback,
    TurnLog,
    InternalThoughts,
    Message,
)


def merge_evaluation(current, new):
    return new if new is not None else current

def merge_plan(current, new):
    return new if new is not None else current


class InterviewState(TypedDict, total=False):
    session_id: str
    candidate_profile: Optional[CandidateProfile]
    interview_plan: Annotated[Optional[InterviewPlan], merge_plan]
    messages: Annotated[list[Message], add_messages]
    conversation_history: list[dict]
    
    current_turn_id: int
    current_user_message: Optional[str]
    current_agent_message: Optional[str]
    previous_agent_message: Optional[str]
    
    answer_analysis: Optional[AnswerAnalysis]
    fact_check_result: Optional[FactCheckResult]
    evaluation: Annotated[Optional[EvaluationState], merge_evaluation]
    router_decision: Optional[RouterDecision]
    question_handler_response: Optional[str]
    internal_thoughts: Optional[InternalThoughts]
    last_thoughts: Optional[dict]
    
    status: Literal["initializing", "in_progress", "ending", "completed"]
    stop_requested: bool
    final_feedback: Optional[FinalFeedback]
    turn_logs: Annotated[list[TurnLog], add]
    last_error: Optional[str]
    asked_questions: list[str]  # Для дедупликации вопросов



def create_initial_state(session_id, candidate_profile):
    return InterviewState(
        session_id=session_id,
        candidate_profile=candidate_profile,
        interview_plan=None,
        messages=[],
        conversation_history=[],
        current_turn_id=1,
        current_user_message=None,
        current_agent_message=None,
        previous_agent_message=None,
        answer_analysis=None,
        fact_check_result=None,
        evaluation=EvaluationState(),
        router_decision=None,
        question_handler_response=None,
        internal_thoughts=None,
        last_thoughts=None,
        status="initializing",
        stop_requested=False,
        final_feedback=None,
        turn_logs=[],
        last_error=None,
        asked_questions=[],
    )
