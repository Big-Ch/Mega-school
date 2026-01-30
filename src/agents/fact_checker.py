# -*- coding: utf-8 -*-
"""Проверка фактов через веб-поиск"""

from src.agents.base import BaseAgent
from src.prompts.templates import FACT_CHECKER_PROMPT, FACT_CHECKER_NO_SEARCH_PROMPT
from src.tools.web_search import create_web_search_tool
from src.models.schemas import FactCheckResult, VerifiedFact, FalseFact, UnverifiedFact
from src.models.output_schemas import FactCheckOutput


class FactCheckerAgent(BaseAgent):
    """Проверяет факты через веб-поиск"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.web_search = create_web_search_tool()
    
    @property
    def name(self):
        return "FactChecker"
    
    async def run(self, state):
        analysis = state.get("answer_analysis")
        
        if not analysis or not analysis.needs_fact_check:
            return {"fact_check_result": FactCheckResult()}
        
        claims = analysis.suspicious_claims
        if not claims:
            return {"fact_check_result": FactCheckResult()}
        
        # Поиск по каждому утверждению
        searchResults = {}
        search_success = False
        
        for claim in claims:
            try:
                res = await self.web_search.verify_fact(claim, context="programming")
                searchResults[claim] = res
                if res.get("found"):
                    search_success = True
            except Exception as e:
                print(f"Search error: {e}")
                searchResults[claim] = {"found": False, "error": str(e)}
        
        # Выбор промпта
        if search_success:
            prompt = FACT_CHECKER_PROMPT.format(
                claims="\n".join([f"- {c}" for c in claims]),
                search_results=self._format_results(searchResults)
            )
        else:
            prompt = FACT_CHECKER_NO_SEARCH_PROMPT.format(
                claims="\n".join([f"- {c}" for c in claims])
            )
        
        try:
            result = await self._call_structured(FactCheckOutput, prompt)
            fact_check = self._convert(result)
        except Exception as e:
            print(f"Error in {self.name}: {e}")
            # Презумпция невиновности - все как unverified
            fact_check = FactCheckResult(
                unverified=[UnverifiedFact(claim=c, reason="web_search_unavailable")
                           for c in claims]
            )
        
        thoughts = state.get("internal_thoughts", {})
        thoughts["fact_checker"] = {
            "claims_checked": claims,
            "search_success": search_success,
            "verified_true_count": len(fact_check.verified_true),
            "verified_false_count": len(fact_check.verified_false),
            "unverified_count": len(fact_check.unverified)
        }
        
        return {"fact_check_result": fact_check,  "internal_thoughts": thoughts}
    

    def _format_results(self, results):
        lines = []
        for claim, r in results.items():
            lines.append(f"\nУтверждение: {claim}")
            if r.get("found"):
                for item in r.get("results", [])[:3]:
                    lines.append(f"  - {item.title}")
            else:
                lines.append(f"  Не найдено")
        return "\n".join(lines)
    
    def _convert(self, output):
        return FactCheckResult(
            verified_true=[VerifiedFact(claim=f.claim, confidence=f.confidence, source=f.source)
                          for f in output.verified_true],
            verified_false=[FalseFact(claim=f.claim, confidence=f.confidence,
                           correct_info=f.correct_info, source=f.source)
                           for f in output.verified_false],
            unverified=[UnverifiedFact(claim=f.claim, reason=f.reason,
                       llm_assessment=f.llm_assessment) for f in output.unverified]
        )
