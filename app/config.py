# RuleRadar AI - Configuration & Settings
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    APP_NAME: str = "RuleRadar AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Storage paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
    UPLOAD_DIR: str = os.path.join(DATA_DIR, "uploads")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(DATA_DIR, 'ruleradar.db')}")
    
    # Processing limits
    MAX_FILE_SIZE_MB: int = 25
    MAX_PDF_PAGES: int = 150
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt"]
    
    # NLP & Model settings
    USE_GPU: bool = False
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    OFFLINE_MODE: bool = True  # Avoid forced remote downloads
    SPACY_MODEL: str = "en_core_web_sm"
    
    # Risk & Importance thresholds
    RISK_THRESHOLD_HIGH: float = 0.70
    RISK_THRESHOLD_MEDIUM: float = 0.40
    IMPORTANCE_THRESHOLD_HIGH: float = 7.0
    IMPORTANCE_THRESHOLD_MEDIUM: float = 4.0
    
    # Comparison thresholds
    COMPARISON_SIMILARITY_THRESHOLD: float = 0.75
    COMPARISON_IDENTICAL_THRESHOLD: float = 0.98

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }

settings = Settings()

# Ensure required directories exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
