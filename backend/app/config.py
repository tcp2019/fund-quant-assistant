from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./fund_quant.db"
    upload_dir: str = "./uploads"
    cors_origins: list[str] = ["http://localhost:5173"]
    auto_sync_enabled: bool = True
    auto_sync_hour: int = 20
    auto_sync_minute: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
