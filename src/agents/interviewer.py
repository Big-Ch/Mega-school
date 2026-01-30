# -*- coding: utf-8 -*-
"""Интервьюер - ведёт диалог с кандидатом"""

from src.agents.base import BaseAgent
from src.prompts.templates import INTERVIEWER_PROMPT, INTERVIEWER_GREETING_PROMPT


class InterviewerAgent(BaseAgent):
    """Ведёт диалог с кандидатом"""
    
    @property
    def name(self):
        return "Interviewer"
    
    async def run(self, state):
        profile = state.get("candidate_profile")
        plan = state.get("interview_plan")
        router = state.get("router_decision")
        qh_response = state.get("question_handler_response")
        asked_questions = state.get("asked_questions", [])
        
        if not profile:
            return {"last_error": "No candidate profile"}
        
        hist = state.get("conversation_history", [])
        history_str = self._format_history(hist)
        
        # Контекст из роутера или плана
        topic = "Общие вопросы"
        difficulty = "medium"
        action = "ask_question"
        hint = None
        
        if router:
            topic = router.next_topic or topic
            difficulty = router.difficulty
            action = router.action
            hint = router.hint
        elif plan and plan.topics:
            for t in plan.topics:
                if t.status in ["pending", "in_progress"]:
                    topic = t.name
                    break
        
        hint_section = ""
        if hint:
            hint_section = f"- Подсказка: {hint}"
        if qh_response:
            hint_section += f"\n- Ответ на вопрос кандидата: {qh_response}"
        
        # Добавляем список уже заданных вопросов для дедупликации
        dedup_section = ""
        if asked_questions:
            dedup_section = f"\n\nВАЖНО: Не повторяй уже заданные вопросы:\n" + "\n".join(f"- {q[:80]}..." if len(q) > 80 else f"- {q}" for q in asked_questions[-5:])
        
        prompt = INTERVIEWER_PROMPT.format(
            candidate_name=profile.name,
            position=profile.position,
            target_grade=profile.target_grade,
            experience=profile.experience,
            current_topic=topic,
            difficulty=difficulty,
            action=action,
            hint_section=hint_section,
            conversation_history=history_str or "Диалог начинается."
        ) + dedup_section
        
        resp = await self._call_llm(prompt)
        msg = resp.strip()
        
        # Защита от JSON в ответе
        if msg.startswith("{") or msg.startswith("```"):
            msg = "Давай продолжим. Расскажи подробнее о своем опыте."
        
        # Сохраняем вопрос для дедупликации
        new_asked = asked_questions + [msg]
        
        return {"current_agent_message": msg,  "asked_questions": new_asked}


    async def generate_greeting(self, state):
        """Приветствие кандидата"""
        profile = state.get("candidate_profile")
        plan = state.get("interview_plan")
        
        if not profile:
            return {"last_error": "No candidate profile"}
        
        topics_str = "Не определены"
        if plan and plan.topics:
            topics_str = ", ".join([t.name for t in plan.topics[:5]])
        
        prompt = INTERVIEWER_GREETING_PROMPT.format(
            candidate_name=profile.name,
            position=profile.position,
            target_grade=profile.target_grade,
            experience=profile.experience,
            topics=topics_str
        )
        
        resp = await self._call_llm(prompt)
        return {"current_agent_message": resp.strip(), "current_turn_id": 1}
    
    def _format_history(self, history):
        if not history:
            return ""
        lines = []
        for entry in history[-10:]:
            role = "Интервьюер" if entry.get("role") == "interviewer" else "Кандидат"
            lines.append(f"{role}: {entry.get('content', '')}")
        return "\n".join(lines)
