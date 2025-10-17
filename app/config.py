from pydantic_settings import BaseSettings
from pydantic import DirectoryPath, PostgresDsn, HttpUrl

class Settings(BaseSettings):
    DATA_DIR: DirectoryPath = "data"
    MAX_PAGE_SIZE: int = 1000
    CACHE_TTL_SECONDS: int = 30
    
    # 数据库连接设置
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    
    # 大模型设置
    LLM_API_BASE_URL: str = "http://localhost:8000/v1"
    LLM_DEFAULT_MODEL: str = "llama3"
    LLM_DEFAULT_MAX_TOKENS: int = 1024
    LLM_DEFAULT_TEMPERATURE: float = 0.7
    LLM_DEFAULT_TOP_P: float = 0.9
    LLM_DEFAULT_TOP_K: int = 40
    LLM_REQUEST_TIMEOUT: int = 120  # 秒
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()