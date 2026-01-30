# -*- coding: utf-8 -*-
"""Логгер интервью"""

import json
from datetime import datetime
from pathlib import Path

from src.config import settings
from src.models.state import InterviewState
from src.models.schemas import TurnLog, FinalFeedback, InternalThoughts


class InterviewLogger:
    """Сохраняет сессии в JSON"""
    
    def __init__(self, log_file_path=None):
        self.base_log_path = Path(log_file_path or settings.log_file_path)
        self.team_name = settings.team_name
        self.current_session_log_path = None
    
    def start_session(self, session_id):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_log_path = self.base_log_path.parent / f"{self.base_log_path.stem}_{session_id}_{timestamp}.json"
        return str(self.current_session_log_path)
    
    @property
    def log_file_path(self):
        return self.current_session_log_path or self.base_log_path
    
    def save_session(self, state):
        log_data = self._build_log_data(state)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2, default=str)
        return str(self.log_file_path)
    
    def _build_log_data(self, state):
        prof = state.get("candidate_profile")
        profile_dict = prof.model_dump() if hasattr(prof, 'model_dump') else dict(prof) if prof else {}
        
        fb = state.get("final_feedback")
        feedback_dict = fb.model_dump() if hasattr(fb, 'model_dump') else None
        
        return {
            "team_name": self.team_name,
            "session_id": state.get("session_id", "unknown"),
            "candidate_profile": profile_dict,
            "turns": [log.model_dump() if hasattr(log, 'model_dump') else dict(log) 
                     for log in state.get("turn_logs", [])],
            "final_feedback": feedback_dict
        }
    
    def get_log_as_string(self, state):
        return json.dumps(self._build_log_data(state), ensure_ascii=False, indent=2, default=str)


    def get_internal_thoughts_display(self, state):
        # Берём last_thoughts (сохранённые после лога) или текущие internal_thoughts
        thoughts = state.get("last_thoughts") or state.get("internal_thoughts")
        if not thoughts:
            return "Ожидание ответа..."
        
        lines = ["=== Мысли агентов ===\n"]
        
        def _get(key):
            return thoughts.get(key) if isinstance(thoughts, dict) else getattr(thoughts, key, None)
        
        aa = _get('answer_analyzer')
        if aa:
            lines.append(f"[AnswerAnalyzer] качество: {aa.get('quality')}, off-topic: {aa.get('off_topic')}")
        
        fc = _get('fact_checker')
        if fc:
            lines.append(f"[FactChecker] проверено: {fc.get('claims_checked')}, верно: {fc.get('verified_true_count')}")
        
        ev = _get('evaluator')
        if ev:
            lines.append(f"[Evaluator] грейд: {ev.get('grade_estimate')}, уверенность: {ev.get('grade_confidence')}")
        
        rt = _get('router')
        if rt:
            lines.append(f"[Router] тема: {rt.get('next_topic')}, действие: {rt.get('action')}")
        
        return "\n".join(lines)
    
    def format_final_feedback(self, feedback):
        if not feedback:
            return "Отчёт не сформирован"
        
        lines = ["=" * 40, "ФИНАЛЬНЫЙ ОТЧЁТ", "=" * 40, ""]
        
        if feedback.decision:
            lines.append(f"Грейд: {feedback.decision.grade}")
            lines.append(f"Рекомендация: {feedback.decision.recommendation}")
            lines.append(f"Уверенность: {feedback.decision.confidence:.0%}\n")
        
        if feedback.technical_review:
            if feedback.technical_review.confirmed_skills:
                lines.append("Навыки: " + ", ".join(feedback.technical_review.confirmed_skills))
            if feedback.technical_review.knowledge_gaps:
                lines.append("Пробелы: " + ", ".join([g.topic for g in feedback.technical_review.knowledge_gaps]))
        
        if feedback.soft_skills:
            lines.append(f"\nSoft: ясность {feedback.soft_skills.clarity:.0%}, "
                        f"честность {feedback.soft_skills.honesty:.0%}, "
                        f"вовлечённость {feedback.soft_skills.engagement:.0%}")
        
        if feedback.roadmap:
            lines.append("\nРазвитие:")
            for item in feedback.roadmap:
                lines.append(f"  - {item.topic}")
        
        if feedback.confidence_trend:
            lines.append(f"\nТренд уверенности: {feedback.confidence_trend}")
        
        return "\n".join(lines)
