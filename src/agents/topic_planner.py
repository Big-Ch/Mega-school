# -*- coding: utf-8 -*-
"""Планировщик тем интервью"""

from src.agents.base import BaseAgent
from src.prompts.templates import TOPIC_PLANNER_PROMPT
from src.models.schemas import InterviewPlan, TopicInfo
from src.models.output_schemas import InterviewPlanOutput


class TopicPlannerAgent(BaseAgent):
    """Создаёт план интервью с темами"""
    
    @property
    def name(self):
        return "TopicPlanner"
    
    async def run(self, state):
        profile = state.get("candidate_profile")
        if not profile:
            return {"last_error": "No candidate profile"}
        
        prompt = TOPIC_PLANNER_PROMPT.format(
            position=profile.position,
            target_grade=profile.target_grade,
            experience=profile.experience
        )
        
        try:
            result = await self._call_structured(InterviewPlanOutput, prompt)
            topics = [TopicInfo(name=t.name, priority=t.priority,
                               questions_budget=t.questions_budget, status=t.status)
                     for t in result.topics]
            plan = InterviewPlan(
                position=result.position,
                target_grade=result.target_grade,
                topics=topics,
                total_questions_limit=result.total_questions_limit
            )
        except Exception as e:
            print(f"Error in {self.name}: {e}")
            plan = self._default_plan(profile)
        
        return {"interview_plan": plan, "status": "in_progress"}
    
    def _default_plan(self, profile):
        """Дефолтный план по позиции"""
        pos = profile.position.lower()
        
        if "backend" in pos or "python" in pos:
            names = ["Python основы", "ООП", "Базы данных", "API", "Git"]
        elif "frontend" in pos:
            names = ["JavaScript", "React/Vue", "HTML/CSS", "HTTP", "Сборка"]
        elif "data" in pos or "ml" in pos:
            names = ["Python", "SQL", "ML/Stats", "Визуализация", "ETL"]
        else:
            names = ["Программирование", "Структуры данных", "БД", "Git", "Тесты"]
        
        topics = [TopicInfo(name=n, priority=i+1, questions_budget=2)
                 for i, n in enumerate(names)]
        
        return InterviewPlan(
            position=profile.position,
            target_grade=profile.target_grade,
            topics=topics,
            total_questions_limit=8
        )
