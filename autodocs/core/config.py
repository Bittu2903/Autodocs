from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None
    SLACK_TOKEN: Optional[str] = None
    
    # Database
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    POSTGRES_URI: str = "postgresql://postgres:12345@localhost:5432/docgen"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Application
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"

settings = Settings()
