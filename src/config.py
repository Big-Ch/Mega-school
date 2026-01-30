# -*- coding: utf-8 -*-
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()



class Settings(BaseSettings):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL", None) or None
    
    team_name: str = os.getenv("TEAM_NAME", "Interview Coach Team")
    log_file_path: str = os.getenv("LOG_FILE_PATH", "interview_log.json")
    
    max_questions_per_topic: int = 5
    total_questions_limit: int= 20
    temperature: float = 0.7
    max_tokens: int = 2000
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()



def validate_settings():
    errs = []
    if not settings.openai_api_key:
        errs.append("OPENAI_API_KEY is required")
    return errs
