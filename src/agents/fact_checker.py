# -*- coding: utf-8 -*-
"""Fact Checker Agent - проверяет факты через веб-поиск"""

from .base import BaseAgent
from src.models.output_schemas import FactCheckOutput
from src.tools.web_search import create_web_search_tool
from src.prompts.templates import FACT_CHECKER_PROMPT


class FactCheckerAgent(BaseAgent):
    """Агент для проверки фактов через веб-поиск"""
    
    def __init__(self):
        super().__init__()
        self.web_search = create_web_search_tool()
    
    async def run(self, state: dict) -> dict:
        analysis = state.get("answer_analysis")
        if not analysis or not analysis.suspicious_claims:
            return {"fact_check_result": None}
        
        claims = analysis.suspicious_claims
        results = []
        
        for claim in claims[:3]:  # Максимум 3 проверки
            try:
                search_result = await self.web_search.verify_fact(claim)
                
                # Анализируем результаты поиска через LLM
                verdict = await self._analyze_claim(claim, search_result)
                results.append(verdict)
            except Exception as e:
                print(f"Fact check error for '{claim}': {e}")
                results.append({
                    "claim": claim,
                    "status": "unverified",
                    "confidence": 0.0,
                    "correct_info": None,
                    "source": None,
                    "reason": str(e)
                })
        
        # Формируем результат
        fact_check_result = {
            "verified_true": [r for r in results if r.get("status") == "verified_true"],
            "verified_false": [r for r in results if r.get("status") == "verified_false"],
            "unverified": [r for r in results if r.get("status") == "unverified"]
        }
        
        # Добавляем в internal_thoughts
        thoughts = state.get("internal_thoughts") or {}
        thoughts["fact_checker"] = {
            "claims_checked": len(claims),
            "verified_true": len(fact_check_result["verified_true"]),
            "verified_false": len(fact_check_result["verified_false"]),
            "unverified": len(fact_check_result["unverified"])
        }
        
        return {
            "fact_check_result": fact_check_result,
            "internal_thoughts": thoughts
        }
    
    async def _analyze_claim(self, claim: str, search_result: dict) -> dict:
        """Анализирует результаты поиска для проверки утверждения"""
        
        if not search_result.get("found") or not search_result.get("results"):
            return {
                "claim": claim,
                "status": "unverified",
                "confidence": 0.0,
                "correct_info": None,
                "source": None,
                "reason": "no_search_results"
            }
        
        # Формируем контекст из результатов поиска
        search_context = "\n".join([
            f"- {r.title}: {r.snippet}" 
            for r in search_result["results"][:3]
        ])
        
        prompt = FACT_CHECKER_PROMPT.format(
            claim=claim,
            search_results=search_context
        )
        
        try:
            llm = self.get_llm().with_structured_output(FactCheckOutput)
            result = await llm.ainvoke(prompt)
            
            return {
                "claim": claim,
                "status": result.status,
                "confidence": result.confidence,
                "correct_info": result.correct_info,
                "source": result.source,
                "reason": result.reasoning
            }
        except Exception as e:
            print(f"LLM analysis error: {e}")
            return {
                "claim": claim,
                "status": "unverified",
                "confidence": 0.0,
                "correct_info": None,
                "source": None,
                "reason": f"llm_error: {e}"
            }
