# -*- coding: utf-8 -*-
"""Базовый класс для агентов"""

import json
import re
from abc import ABC, abstractmethod
from typing import TypeVar

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.config import settings

T = TypeVar('T', bound=BaseModel)



class BaseAgent(ABC):
    """Базовый класс агентов"""
    
    def __init__(self, model=None, temperature=None):
        self.model_name = model or settings.openai_model
        self.temperature = temperature or settings.temperature
        
        llm_kwargs = {
            "model": self.model_name,
            "temperature": self.temperature,
            "api_key": settings.openai_api_key,
            "max_tokens": settings.max_tokens,
        }
        
        # Прокси если настроен
        if settings.openai_base_url:
            llm_kwargs["base_url"] = settings.openai_base_url
        
        self.llm = ChatOpenAI(**llm_kwargs)
    
    @property
    @abstractmethod
    def name(self):
        pass
    
    @abstractmethod
    async def run(self, state):
        pass
    
    async def _call_llm(self, system_prompt, user_prompt=""):
        """Простой вызов LLM"""
        msgs = [SystemMessage(content=system_prompt)]
        if user_prompt:
            msgs.append(HumanMessage(content=user_prompt))
        resp = await self.llm.ainvoke(msgs)
        return resp.content
    

    async def _call_structured(self, schema, system_prompt, user_prompt=""):
        """Вызов LLM со структурированным выводом"""
        structured_llm = self.llm.with_structured_output(schema)
        msgs = [SystemMessage(content=system_prompt)]
        if user_prompt:
            msgs.append(HumanMessage(content=user_prompt))
        return await structured_llm.ainvoke(msgs)
    
    def _parse_json(self, response):
        """Парсинг JSON из ответа"""
        cleaned = response.strip()
        
        # Ищем JSON в code blocks
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned)
        if match:
            cleaned = match.group(1)
        
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            cleaned = match.group(0)
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"JSON error in {self.name}: {e}")
            return {}
