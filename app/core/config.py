from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    X_API_KEY: str = Field(..., env="X_API_KEY")
    CHUNK_SIZE: int = Field(500, env="CHUNK_SIZE")
    TOP_K: int = Field(5, env="TOP_K")
    MODEL: str = Field("gpt-3.5-turbo", env="MODEL")
    RATE_LIMIT: int = Field(60, env="RATE_LIMIT")

    class Config:
        env_file = ".env"  # Load from .env file

settings = Settings()

