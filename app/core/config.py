# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Required
    openai_api_key: str
    api_key: str = "changeme"

    # Optional with defaults
    model_name: str = "gpt-4o-mini"
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5
    rate_limit_rpm: int = 60
    docs_path: str = "./docs"
    index_path: str = "./faiss_index/index.faiss"
    meta_path: str = "./faiss_index/index.pkl"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        frozen = False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()  # backward-compatible singleton — nothing else breaks

