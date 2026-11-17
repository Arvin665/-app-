from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中管理运行参数；生产值全部通过环境变量注入。"""

    app_name: str = "商办信息资产库 API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./asset_library.db"
    redis_url: str = "redis://localhost:6379/0"
    sensitive_field_key: str = "development-only-sensitive-key-change-me"
    bootstrap_invite_code: str = "246810"
    public_base_url: str = "http://localhost:8000"
    cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175,http://127.0.0.1:5176,"
        "https://localhost,capacitor://localhost"
    )
    upload_dir: str = str(Path(__file__).resolve().parents[2] / "uploads")
    # auto 会在配置 API Key 时优先调用 DeepSeek，否则保留本地规则。
    ai_provider: str = "auto"
    ocr_enabled: bool = True
    ocr_max_pdf_pages: int = 30
    ocr_min_text_chars: int = 20
    asr_timeout_seconds: int = 180
    asr_engine: str = "auto"
    vosk_model_path: str = ""
    sense_voice_model_path: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout_seconds: int = 45
    ffmpeg_binary: str = ""
    auto_create_tables: bool = True
    access_cache_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的跨域白名单转换为列表。"""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """单例读取环境变量，避免同一进程内出现配置漂移。"""
    return Settings()


settings = get_settings()
