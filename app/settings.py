import os
from pydantic import BaseSettings, AnyHttpUrl
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "researcher-bot"
    debug: bool = False

    # Suche
    search_provider: str = "duckduckgo"  # aktuell unterstützt: duckduckgo
    http_timeout: float = 15.0
    user_agent: str = "researcher-bot/0.1 (+https://example.org)"

    # Summarization via Ollama (optional)
    ollama_base_url: Optional[AnyHttpUrl] = None  # z.B. http://localhost:11434
    ollama_model: str = "llama3.1"
    ollama_max_tokens: int = 400
    ollama_temperature: float = 0.2

    # Inbound-Auth (optional)
    inbound_token: Optional[str] = os.getenv("RESEARCHER_INBOUND_TOKEN")

    class Config:
        env_file = ".env"


settings = Settings()
