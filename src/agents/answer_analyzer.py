# -*- coding: utf-8 -*-
"""Анализатор ответов кандидата"""

from src.agents.base import BaseAgent
from src.prompts.templates import ANSWER_ANALYZER_PROMPT
from src.models.schemas import AnswerAnalysis
from src.models.output_schemas import AnswerAnalysisOutput



class AnswerAnalyzerAgent(BaseAgent):
    """Анализирует ответы кандидата"""
    
    @property
    def name(self):
        return "AnswerAnalyzer"
    
    async def run(self, state):
        profile = state.get("candidate_profile")
        user_msg = state.get("current_user_message")
        hist = state.get("conversation_history", [])
        plan = state.get("interview_plan")
        
        if not user_msg:
            return {"last_error": "No user message"}
        
        # Последний вопрос
        last_question = "Вопрос"
        for entry in reversed(hist):
            if entry.get("role") == "interviewer":
                last_question = entry.get("content", last_question)
                break
        
        # Текущая тема
        current_topic = "Общие"
        if plan and plan.topics:
            for t in plan.topics:
                if t.status in ["pending", "in_progress"]:
                    current_topic = t.name
                    break
        
        prompt = ANSWER_ANALYZER_PROMPT.format(
            position=profile.position if profile else "Developer",
            target_grade=profile.target_grade if profile else "Junior",
            current_topic=current_topic,
            last_question=last_question,
            user_message=user_msg
        )
        
        try:
            res = await self._call_structured(AnswerAnalysisOutput, prompt)
            analysis = AnswerAnalysis(
                quality=res.quality,
                confidence_detected=res.confidence_detected,
                completeness=res.completeness,
                off_topic=res.off_topic,
                needs_fact_check=res.needs_fact_check,
                suspicious_claims=res.suspicious_claims,
                candidate_asked_question=res.candidate_asked_question,
                candidate_question=res.candidate_question,
                reasoning=res.reasoning
            )
        except Exception as e:
            print(f"Error in {self.name}: {e}")
            analysis = self._fallback(user_msg)
        
        thoughts = {
            "answer_analyzer": {
                "quality": analysis.quality,
                "confidence_detected": analysis.confidence_detected,
                "off_topic": analysis.off_topic,
                "needs_fact_check": analysis.needs_fact_check,
                "suspicious_claims": analysis.suspicious_claims,
                "reasoning": analysis.reasoning
            }
        }
        
        return {"answer_analysis": analysis, "internal_thoughts": thoughts}
    

    def _fallback(self, msg):
        """Fallback анализ по эвристикам"""
        has_question = "?" in msg
        wordCount = len(msg.split())
        
        if wordCount < 5:
            quality = "poor"
        elif wordCount < 20:
            quality = "partial"
        elif wordCount < 50:
            quality = "good"
        else:
            quality = "excellent"
        
        return AnswerAnalysis(
            quality=quality,
            confidence_detected=0.5,
            completeness=min(wordCount / 50, 1.0),
            off_topic=False,
            needs_fact_check=False,
            suspicious_claims=[],
            candidate_asked_question=has_question,
            candidate_question=msg if has_question else None,
            reasoning="Fallback анализ"
        )
