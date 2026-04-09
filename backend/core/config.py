from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Interview Assistant"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]

    # DeepSeek (primary LLM)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # Aliyun ASR (NLS)
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""
    aliyun_asr_app_key: str = ""

    # Aliyun dashscope (Embedding)
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_embedding_model: str = "text-embedding-v2"

    # Qwen3 (fallback LLM)
    qwen3_api_key: str = ""
    qwen3_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen3_model: str = "qwen3-14b"

    # Elasticsearch
    es_url: str = "http://localhost:9200"
    es_index: str = "interview_kb"
    es_username: str = ""
    es_password: str = ""
    es_score_threshold: float = 0.85

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_context_ttl: int = 7200       # 2h — sliding context window
    redis_questions_ttl: int = 604800   # 7d — full question list for export

    class Config:
        env_file = "backend/.env"
        extra = "ignore"


settings = Settings()
