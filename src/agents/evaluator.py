# -*- coding: utf-8 -*-
"""Оценщик - накапливает оценку кандидата"""

import json
from src.agents.base import BaseAgent
from src.prompts.templates import EVALUATOR_PROMPT
from src.models.schemas import EvaluationState, SkillConfirmed, SkillGap, SoftSkills
from src.models.output_schemas import EvaluationOutput



class EvaluatorAgent(BaseAgent):
    """Накапливает оценку кандидата"""
    
    @property
    def name(self):
        return "Evaluator"
    
    async def run(self, state):
        profile = state.get("candidate_profile")
        user_msg = state.get("current_user_message")
        analysis = state.get("answer_analysis")
        fact_check = state.get("fact_check_result")
        current_eval = state.get("evaluation") or EvaluationState()
        plan = state.get("interview_plan")
        turn_id = state.get("current_turn_id", 1)
        history = state.get("conversation_history", [])
        
        if not user_msg or not analysis:
            return {}
        
        # Последний вопрос
        last_question = "Вопрос"
        for entry in reversed(history):
            if entry.get("role") == "interviewer":
                last_question = entry.get("content", last_question)
                break
        
        # Тема
        topic= "Общие"
        if plan and plan.topics:
            for t in plan.topics:
                if t.status in ["pending", "in_progress"]:
                    topic = t.name
                    break
        
        eval_dict = current_eval.model_dump()
        fc_str = json.dumps(fact_check.model_dump(), ensure_ascii=False) if fact_check else "Нет"
        
        prompt = EVALUATOR_PROMPT.format(
            position=profile.position if profile else "Developer",
            target_grade=profile.target_grade if profile else "Junior",
            current_topic=topic,
            last_question=last_question,
            user_message=user_msg,
            answer_analysis=json.dumps(analysis.model_dump(), ensure_ascii=False),
            fact_check=fc_str,
            current_evaluation=json.dumps(eval_dict, ensure_ascii=False),
            turn_id=turn_id
        )
        
        try:
            result = await self._call_structured(EvaluationOutput, prompt)
            new_eval = self._merge(result, current_eval, turn_id)
            # Добавляем уверенность в историю
            new_eval.confidence_history = current_eval.confidence_history + [result.grade_confidence]
            reasoning = result.reasoning
        except Exception as e:
            print(f"Error in {self.name}: {e}")
            return self._basic_update(current_eval, analysis, fact_check)
        
        thoughts = state.get("internal_thoughts", {})
        thoughts["evaluator"] = {
            "grade_estimate": new_eval.current_grade_estimate,
            "grade_confidence": new_eval.grade_confidence,
            "skills_confirmed_count": len(new_eval.skills_confirmed),
            "skills_gaps_count": len(new_eval.skills_gaps),
            "reasoning": reasoning
        }
        
        return {"evaluation": new_eval, "internal_thoughts": thoughts}
    

    def _merge(self, output, current, turn_id):
        """Слияние оценок"""
        # Навыки
        confirmed = {s.skill: s for s in current.skills_confirmed}
        for item in output.skills_confirmed:
            if item.skill in confirmed:
                old = confirmed[item.skill]
                confirmed[item.skill] = SkillConfirmed(
                    skill=item.skill,
                    confidence=max(old.confidence, item.confidence),
                    evidence=old.evidence + [f"turn {turn_id}"]
                )
            else:
                confirmed[item.skill] = SkillConfirmed(
                    skill=item.skill, confidence=item.confidence,
                    evidence=[f"turn {turn_id}"]
                )
        
        # Пробелы
        gaps = {g.skill: g for g in current.skills_gaps}
        for item in output.skills_gaps:
            if item.skill not in gaps:
                gaps[item.skill] = SkillGap(skill=item.skill, severity=item.severity,
                                           failed_at=f"turn {turn_id}")
        
        return EvaluationState(
            skills_confirmed=list(confirmed.values()),
            skills_gaps=list(gaps.values()),
            soft_skills=SoftSkills(
                clarity=output.soft_skills.clarity,
                honesty=output.soft_skills.honesty,
                engagement=output.soft_skills.engagement
            ),
            hallucinations_detected=output.hallucinations_detected,
            off_topic_attempts=output.off_topic_attempts,
            current_grade_estimate=output.current_grade_estimate,
            grade_confidence=output.grade_confidence
        )
    
    def _basic_update(self, current, analysis, fact_check):
        """Базовое обновление при ошибке"""
        hallucinations = current.hallucinations_detected
        if fact_check and fact_check.verified_false:
            hallucinations += len(fact_check.verified_false)
        
        off_topic = current.off_topic_attempts
        if analysis and analysis.off_topic:
            off_topic += 1
        
        new_eval = EvaluationState(
            skills_confirmed=current.skills_confirmed,
            skills_gaps=current.skills_gaps,
            soft_skills=current.soft_skills,
            hallucinations_detected=hallucinations,
            off_topic_attempts=off_topic,
            current_grade_estimate=current.current_grade_estimate,
            grade_confidence=current.grade_confidence
        )
        return {"evaluation": new_eval}
