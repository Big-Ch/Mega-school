# -*- coding: utf-8 -*-
"""Полный граф интервью на LangGraph с conditional edges"""

from typing import Literal
from langgraph.graph import StateGraph, END

from src.models.state import InterviewState, create_initial_state
from src.models.schemas import (
    CandidateProfile, RouterDecision, TurnLog, InternalThoughts, EvaluationState
)
from src.agents import (
    TopicPlannerAgent, InterviewerAgent, AnswerAnalyzerAgent,
    FactCheckerAgent, EvaluatorAgent, QuestionHandlerAgent, HiringManagerAgent
)
from src.config import settings



class InterviewGraph:
    def __init__(self, logger=None):
        self.topic_planner = TopicPlannerAgent()
        self.interviewer = InterviewerAgent()
        self.answer_analyzer = AnswerAnalyzerAgent()
        self.fact_checker = FactCheckerAgent()
        self.evaluator = EvaluatorAgent()
        self.question_handler = QuestionHandlerAgent()
        self.hiring_manager = HiringManagerAgent()
        self.logger = logger
        
        self.app = self._build_full_graph().compile()
    
    def set_logger(self, logger):
        self.logger = logger
    
    def _build_full_graph(self):
        graph = StateGraph(InterviewState)
        
        # Все ноды
        graph.add_node("entry_router", self._entry_router)
        graph.add_node("topic_planner", self._run_topic_planner)
        graph.add_node("greeting", self._run_greeting)
        graph.add_node("log_greeting", self._log_greeting)
        graph.add_node("prepare_turn", self._prepare_turn)
        graph.add_node("check_stop", self._check_stop)
        graph.add_node("check_limit", self._check_limit)
        graph.add_node("answer_analyzer", self._run_answer_analyzer)
        graph.add_node("fact_checker", self._run_fact_checker)
        graph.add_node("evaluator", self._run_evaluator)
        graph.add_node("question_handler", self._run_question_handler)
        graph.add_node("router", self._run_router)
        graph.add_node("interviewer", self._run_interviewer)
        graph.add_node("log_turn", self._run_log_turn)
        graph.add_node("update_progress", self._update_topic_progress)
        graph.add_node("hiring_manager", self._run_hiring_manager)
        
        graph.set_entry_point("entry_router")
        
        # Роутинг входа
        graph.add_conditional_edges("entry_router", self._route_entry, {
            "init": "topic_planner",
            "turn": "prepare_turn"
        })
        
        # Инициализация
        graph.add_edge("topic_planner", "greeting")
        graph.add_edge("greeting", "log_greeting")
        graph.add_edge("log_greeting", END)
        
        # Подготовка хода -> проверка стоп
        graph.add_edge("prepare_turn", "check_stop")
        
        # Стоп или продолжение
        graph.add_conditional_edges("check_stop", self._route_stop, {
            "stop": "hiring_manager",
            "continue": "check_limit"
        })
        
        # Лимит ходов
        graph.add_conditional_edges("check_limit", self._route_limit, {
            "limit": "hiring_manager",
            "continue": "answer_analyzer"
        })
        
        # После анализа: нужна ли проверка фактов
        graph.add_conditional_edges("answer_analyzer", self._route_fact_check, {
            "check": "fact_checker",
            "skip": "evaluator"
        })
        
        graph.add_edge("fact_checker", "evaluator")
        
        # После оценки: есть ли вопрос кандидата
        graph.add_conditional_edges("evaluator", self._route_question, {
            "has_question": "question_handler",
            "no_question": "router"
        })
        
        graph.add_edge("question_handler", "router")
        
        # После роутера: завершать или продолжать
        graph.add_conditional_edges("router", self._route_end, {
            "end": "hiring_manager",
            "continue": "interviewer"
        })
        
        graph.add_edge("interviewer", "log_turn")
        graph.add_edge("log_turn", "update_progress")
        graph.add_edge("update_progress", END)
        
        graph.add_edge("hiring_manager", END)
        
        return graph
    
    def _route_entry(self, state) -> Literal["init", "turn"]:
        if state.get("status") == "initializing":
            return "init"
        return "turn"
    
    def _route_stop(self, state) -> Literal["stop", "continue"]:
        if state.get("stop_requested"):
            return "stop"
        return "continue"
    
    def _route_limit(self, state) -> Literal["limit", "continue"]:
        turn = state.get("current_turn_id", 1)
        if turn >= settings.total_questions_limit:
            return "limit"
        return "continue"
    
    def _route_fact_check(self, state) -> Literal["check", "skip"]:
        analysis = state.get("answer_analysis")
        if analysis and analysis.needs_fact_check and analysis.suspicious_claims:
            return "check"
        return "skip"
    
    def _route_question(self, state) -> Literal["has_question", "no_question"]:
        analysis = state.get("answer_analysis")
        if analysis and analysis.candidate_asked_question:
            return "has_question"
        return "no_question"
    
    def _route_end(self, state) -> Literal["end", "continue"]:
        decision = state.get("router_decision")
        if decision and decision.action == "end_interview":
            return "end"
        return "continue"
    

    async def _entry_router(self, state):
        return state
    
    async def _run_topic_planner(self, state):
        result = await self.topic_planner.run(dict(state))
        return {**state, **result}
    
    async def _run_greeting(self, state):
        result = await self.interviewer.generate_greeting(dict(state))
        history = state.get("conversation_history", [])
        msg = result.get("current_agent_message", "")
        if msg:
            history = history + [{"role": "interviewer", "content": msg}]
        return {
            **state, **result,
            "conversation_history": history,
            "status": "in_progress",
            "previous_agent_message": msg
        }
    
    async def _log_greeting(self, state):
        return await self._log_turn_internal(state, is_greeting=True)
    
    async def _prepare_turn(self, state):
        user_message = state.get("current_user_message", "")
        prev_msg = state.get("current_agent_message", "")
        history = state.get("conversation_history", [])
        history = history + [{"role": "candidate", "content": user_message}]
        turn = state.get("current_turn_id", 1)
        
        # Проверка стоп-слов
        stop_requested = any(kw in user_message.lower() for kw in ["стоп", "stop", "завершить"])
        
        return {
            **state,
            "previous_agent_message": prev_msg,
            "conversation_history": history,
            "current_turn_id": turn + 1,
            "answer_analysis": None,
            "fact_check_result": None,
            "router_decision": None,
            "question_handler_response": None,
            "stop_requested": stop_requested,
            "status": "ending" if stop_requested else state.get("status")
        }
    
    async def _check_stop(self, state):
        return state
    
    async def _check_limit(self, state):
        turn = state.get("current_turn_id", 1)
        if turn >= settings.total_questions_limit:
            return {**state, "status": "ending"}
        return state
    
    async def _run_answer_analyzer(self, state):
        result = await self.answer_analyzer.run(dict(state))
        return {**state, **result}
    
    async def _run_fact_checker(self, state):
        result = await self.fact_checker.run(dict(state))
        return {**state, **result}
    
    async def _run_evaluator(self, state):
        result = await self.evaluator.run(dict(state))
        return {**state, **result}
    
    async def _run_question_handler(self, state):
        result = await self.question_handler.run(dict(state))
        return {**state, **result}
    
    async def _run_router(self, state):
        decision = self._make_routing_decision(state)
        thoughts = state.get("internal_thoughts") or {}
        thoughts["router"] = {
            "next_topic": decision.next_topic,
            "difficulty": decision.difficulty,
            "action": decision.action,
            "reasoning": decision.reasoning
        }
        return {**state, "router_decision": decision, "internal_thoughts": thoughts}
    
    async def _run_interviewer(self, state):
        result = await self.interviewer.run(dict(state))
        history = state.get("conversation_history", [])
        
        qh = state.get("question_handler_response")
        if qh:
            history = history + [{"role": "interviewer", "content": qh}]
        if result.get("current_agent_message"):
            history = history + [{"role": "interviewer", "content": result["current_agent_message"]}]
        
        return {
            **state, **result,
            "conversation_history": history,
            "question_handler_response": None,
            "router_decision": None
        }
    
    async def _run_log_turn(self, state):
        return await self._log_turn_internal(state, is_greeting=False)
    
    async def _update_topic_progress(self, state):
        plan = state.get("interview_plan")
        if not plan or not plan.topics:
            return {**state, "previous_agent_message": state.get("current_agent_message", "")}
        
        for t in plan.topics:
            if t.status in ["pending", "in_progress"]:
                t.status = "in_progress"
                t.questions_asked += 1
                if t.questions_asked >= t.questions_budget:
                    t.status = "completed"
                break
        
        return {
            **state,
            "interview_plan": plan,
            "previous_agent_message": state.get("current_agent_message", "")
        }
    
    async def _run_hiring_manager(self, state):
        result = await self.hiring_manager.run(dict(state))
        new_state = {**state, **result, "status": "completed"}
        if self.logger:
            self.logger.save_session(new_state)
        return new_state
    
    async def _log_turn_internal(self, state, is_greeting=False):
        logs = state.get("turn_logs", [])
        thoughts = state.get("internal_thoughts") or {}
        
        if is_greeting:
            turn_log = TurnLog(
                turn_id=1,
                agent_visible_message=state.get("current_agent_message", ""),
                user_message=None,
                internal_thoughts=InternalThoughts(**thoughts)
            )
        else:
            turn_log = TurnLog(
                turn_id=state.get("current_turn_id", 1),
                agent_visible_message=state.get("previous_agent_message", ""),
                user_message=state.get("current_user_message"),
                internal_thoughts=InternalThoughts(**thoughts)
            )
        
        new_logs = logs + [turn_log]
        new_state = {**state, "turn_logs": new_logs, "internal_thoughts": None, "last_thoughts": thoughts}
        
        if self.logger:
            self.logger.save_session(new_state)
        return new_state
    
    def _make_routing_decision(self, state):
        analysis = state.get("answer_analysis")
        plan = state.get("interview_plan")
        
        decision = RouterDecision(
            next_topic="Общие вопросы", difficulty="medium",
            action="ask_question", reasoning="Продолжаем"
        )
        
        if not plan or not plan.topics:
            return decision
        
        current = None
        for t in plan.topics:
            if t.status in ["pending", "in_progress"]:
                current = t
                break
        
        if not current:
            decision.action = "end_interview"
            decision.reasoning = "Все темы рассмотрены"
            return decision
        
        decision.next_topic = current.name
        
        if analysis:
            if analysis.quality == "excellent":
                decision.difficulty = "hard"
                decision.action = "ask_followup"
            elif analysis.quality == "good":
                decision.action = "ask_question"
            elif analysis.quality == "partial":
                decision.action = "ask_followup"
            elif analysis.quality == "poor":
                decision.difficulty = "easy"
                decision.action = "give_hint"
                decision.hint = "Подумай о базовых концепциях"
            
            if analysis.off_topic:
                decision.action = "ask_question"
        
        if current.questions_asked >= current.questions_budget:
            next_t = self._get_next_topic(plan, current)
            if next_t:
                decision.next_topic = next_t.name
                decision.action = "change_topic"
            else:
                decision.action = "end_interview"
        
        return decision
    
    def _get_next_topic(self, plan, current):
        found = False
        for t in plan.topics:
            if t.name == current.name:
                found = True
                continue
            if found and t.status == "pending":
                return t
        return None


    async def start_interview(self, profile, session_id):
        initial = create_initial_state(session_id, profile)
        return await self.app.ainvoke(initial)
    
    async def process_user_message(self, state, user_message):
        state = {**state, "current_user_message": user_message}
        return await self.app.ainvoke(state)


def create_interview_graph():
    return InterviewGraph()
