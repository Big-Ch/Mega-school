# -*- coding: utf-8 -*-
"""Обработчик вопросов от кандидата"""

from src.agents.base import BaseAgent
from src.prompts.templates import QUESTION_HANDLER_PROMPT
from src.models.output_schemas import QuestionHandlerOutput


class QuestionHandlerAgent(BaseAgent):
    """Отвечает на вопросы кандидата"""
    
    @property
    def name(self):
        return "QuestionHandler"
    
    async def run(self, state):
        analysis = state.get("answer_analysis")
        profile = state.get("candidate_profile")
        plan = state.get("interview_plan")
        
        if not analysis or not analysis.candidate_asked_question:
            return {}
        
        question = analysis.candidate_question or "вопрос"
        
        # Текущая тема
        topic = "Общие"
        if plan and plan.topics:
            for t in plan.topics:
                if t.status in ["pending", "in_progress"]:
                    topic = t.name
                    break
        
        prompt = QUESTION_HANDLER_PROMPT.format(
            candidate_question=question,
            position=profile.position if profile else "Developer",
            current_topic=topic
        )
        
        try:
            result = await self._call_structured(QuestionHandlerOutput, prompt)
            response = result.response
            detected = result.question_detected
        except Exception as e:
            print(f"Error in {self.name}: {e}")
            response = self._fallback(question, profile)
            detected = question
        
        thoughts = state.get("internal_thoughts", {})
        thoughts["question_handler"] = {"question_detected": detected, "response_generated": True}
        
        return {"question_handler_response": response, "internal_thoughts": thoughts}
    
    def _fallback(self, question, profile):
        q = question.lower()
        pos = profile.position if profile else "разработчика"
        
        # Защита от prompt injection
        injection_words = ["правильный ответ", "подскажи ответ", "скажи решение", 
                         "забудь инструкции", "игнорируй", "ты теперь"]
        if any(w in q for w in injection_words):
            return "Я не могу подсказать ответ на этот вопрос. Попробуй порассуждать своими словами."
        
        # Вопросы о вакансии - развёрнутые ответы
        if any(w in q for w in ["вакан", "позиц", "должност", "описан"]):
            return (f"Позиция {pos} предполагает работу над продуктовыми задачами в команде из 5-7 человек. "
                   f"Вы будете участвовать в разработке новых фич, код-ревью и технических обсуждениях. "
                   f"Есть возможность влиять на архитектурные решения и предлагать улучшения.")
        
        if any(w in q for w in ["задач", "проект", "испытательн"]):
            return (f"На испытательном сроке для {pos} вы начнёте с небольших задач для знакомства с кодовой базой. "
                   f"К вам будет прикреплён ментор, который поможет с онбордингом. "
                   f"Обычно через 2-3 недели переходите к более сложным задачам.")
        
        if any(w in q for w in ["стек", "технолог"]):
            return ("Мы используем современный стек: Python/Go для бэкенда, PostgreSQL, Redis, Docker, Kubernetes. "
                   "CI/CD через GitLab, мониторинг в Grafana. Код-ревью обязательны для всех изменений.")
        
        if any(w in q for w in ["команд", "коллектив", "структур"]):
            return ("Команды кросс-функциональные: разработчики, QA, продакт-менеджер, дизайнер. "
                   "Работаем по Scrum, спринты 2 недели. Есть ежедневные стендапы и еженедельные техтоки.")
        
        if any(w in q for w in ["рост", "карьер", "развит"]):
            return ("У нас прозрачная система грейдов с понятными критериями. Есть бюджет на обучение и конференции. "
                   "Проводим внутренние митапы, есть программа менторства для роста в техлида.")
        
        return "Хороший вопрос! Обсудим детали после технической части. Давай продолжим."
