import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    API_KEY = os.getenv("SERVICE_API_KEY", "changeme")  # For X-API-Key
    MODEL = os.getenv("MODEL_NAME", "gpt-4o")
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 512))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 64))
    TOP_K = int(os.getenv("TOP_K", 5))
    RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", 60))
    DOCS_PATH = os.getenv("DOCS_PATH", "./docs")
    INDEX_PATH = os.getenv("INDEX_PATH", "./faiss_index/index.faiss")
    META_PATH = os.getenv("META_PATH", "./faiss_index/index.pkl")

settings = Settings()
