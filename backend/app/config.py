from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./fund_quant.db"
    upload_dir: str = "./uploads"
    cors_origins: list[str] = ["http://localhost:5173"]
    auto_sync_enabled: bool = True
    auto_sync_hour: int = 20
    auto_sync_minute: int = 5

    # LLM (AI signal interpretation)
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"


settings = Settings()
