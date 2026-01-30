# -*- coding: utf-8 -*-
"""Hiring Manager - формирует финальный отчёт"""

import json
from src.agents.base import BaseAgent
from src.prompts.templates import HIRING_MANAGER_PROMPT
from src.models.schemas import (
    FinalFeedback, Decision, TechnicalReview,
    KnowledgeGap, RoadmapItem, SoftSkills
)
from src.models.output_schemas import FinalFeedbackOutput



class HiringManagerAgent(BaseAgent):
    """Формирует финальный отчёт"""
    
    @property
    def name(self):
        return "HiringManager"
    
    async def run(self, state):
        profile = state.get("candidate_profile")
        evaluation = state.get("evaluation")
        hist = state.get("conversation_history", [])
        
        if not profile:
            return {"last_error": "No candidate profile"}
        
        # Ложные факты
        false_facts = []
        fc = state.get("fact_check_result")
        if fc and fc.verified_false:
            for f in fc.verified_false:
                false_facts.append({"claim": f.claim, "correct_info": f.correct_info})
        
        eval_str = json.dumps(evaluation.model_dump(), ensure_ascii=False) if evaluation else "Нет"
        conv_summary = self._summarize(hist)
        ff_str = "\n".join([f"- {f['claim']}" for f in false_facts]) or "Нет"
        
        prompt = HIRING_MANAGER_PROMPT.format(
            candidate_name=profile.name,
            position=profile.position,
            target_grade=profile.target_grade,
            experience=profile.experience,
            final_evaluation=eval_str,
            conversation_summary=conv_summary,
            false_facts=ff_str
        )
        
        try:
            result = await self._call_structured(FinalFeedbackOutput, prompt)
            feedback = self._convert(result, evaluation)
        except Exception as e:
            print(f"Error in {self.name}: {e}")
            feedback = self._fallback(profile, evaluation)
        
        return {"final_feedback": feedback, "status": "completed"}
    

    def _summarize(self, history):
        if not history:
            return "Диалог не состоялся"
        lines = []
        for i, entry in enumerate(history[-20:], 1):
            role = "И" if entry.get("role") == "interviewer" else "К"
            content = entry.get("content", "")[:80]
            lines.append(f"{i}. [{role}]: {content}...")
        return "\n".join(lines)
    
    def _compute_trend(self, evaluation):
        """Вычисляет тренд уверенности"""
        if not evaluation or not evaluation.confidence_history:
            return "→ недостаточно данных"
        
        hist = evaluation.confidence_history
        if len(hist) < 2:
            return "→ недостаточно данных"
        
        # Сравниваем первую и вторую половину
        mid = len(hist) // 2
        first_half = sum(hist[:mid]) / max(mid, 1)
        second_half = sum(hist[mid:]) / max(len(hist) - mid, 1)
        
        diff = second_half - first_half
        if diff > 0.1:
            return f"↗ уверенность росла ({first_half:.0%} → {second_half:.0%})"
        elif diff < -0.1:
            return f"↘ уверенность падала ({first_half:.0%} → {second_half:.0%})"
        else:
            return f"→ стабильно (~{sum(hist)/len(hist):.0%})"
    

    def _convert(self, output, evaluation=None):
        return FinalFeedback(
            decision=Decision(
                grade=output.decision.grade,
                recommendation=output.decision.recommendation,
                confidence=output.decision.confidence
            ),
            technical_review=TechnicalReview(
                confirmed_skills=output.technical_review.confirmed_skills,
                knowledge_gaps=[KnowledgeGap(topic=g.topic, correct_answer=g.correct_answer)
                               for g in output.technical_review.knowledge_gaps]
            ),
            soft_skills=SoftSkills(
                clarity=output.soft_skills.clarity,
                honesty=output.soft_skills.honesty,
                engagement=output.soft_skills.engagement
            ),
            roadmap=[RoadmapItem(topic=r.topic, resources=r.resources)
                    for r in output.roadmap],
            confidence_trend=self._compute_trend(evaluation)
        )
    
    def _fallback(self, profile, evaluation):
        grade = evaluation.current_grade_estimate if evaluation else "Junior"
        recommendation = "Hire"
        
        if evaluation:
            if evaluation.hallucinations_detected > 2 or len(evaluation.skills_gaps) > 3:
                recommendation = "No Hire"
        
        return FinalFeedback(
            decision=Decision(grade=grade, recommendation=recommendation, confidence=0.5),
            technical_review=TechnicalReview(
                confirmed_skills=[s.skill for s in evaluation.skills_confirmed] if evaluation else [],
                knowledge_gaps=[KnowledgeGap(topic=g.skill, correct_answer="")
                               for g in evaluation.skills_gaps] if evaluation else []
            ),
            soft_skills=evaluation.soft_skills if evaluation else SoftSkills(),
            roadmap=[],
            confidence_trend=self._compute_trend(evaluation)
        )
