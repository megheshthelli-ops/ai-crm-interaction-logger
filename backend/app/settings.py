from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "gemma2-9b-it"
    database_url: str = "sqlite:///./ai_crm_hcp.db"
    cors_origins: str = (
        "http://localhost:5173,http://localhost:3000,http://localhost:5174,http://localhost:5175"
    )
    debug: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def groq_configured(self) -> bool:
        key = self.groq_api_key.strip()
        return bool(key) and key != "your_groq_api_key_here"


settings = Settings()
