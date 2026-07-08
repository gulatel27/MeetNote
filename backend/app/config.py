from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Meeting Report Tool API"
    api_prefix: str = "/api"

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_stt_model: str = Field(default="whisper-1", alias="OPENAI_STT_MODEL")
    openai_summary_model: str = Field(default="gpt-5.5", alias="OPENAI_SUMMARY_MODEL")
    openai_vision_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_VISION_MODEL")
    stt_provider: str = Field(default="openai", alias="STT_PROVIDER")
    openai_stt_max_bytes: int = Field(default=24 * 1024 * 1024, alias="OPENAI_STT_MAX_BYTES")
    stt_chunk_seconds: int = Field(default=600, alias="STT_CHUNK_SECONDS")
    ffmpeg_path: str = Field(default="ffmpeg", alias="FFMPEG_PATH")

    database_url: str = Field(default="sqlite:///./meeting_reports.db", alias="DATABASE_URL")
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    image_dir: str = Field(default="./uploads/images", alias="IMAGE_DIR")
    report_dir: str = Field(default="./reports", alias="REPORT_DIR")
    max_upload_bytes: int = Field(default=500 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")
    max_image_bytes: int = Field(default=20 * 1024 * 1024, alias="MAX_IMAGE_BYTES")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    @property
    def upload_path(self) -> Path:
        return self._resolve_backend_path(self.upload_dir)

    @property
    def image_path(self) -> Path:
        return self._resolve_backend_path(self.image_dir)

    @property
    def report_path(self) -> Path:
        return self._resolve_backend_path(self.report_dir)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def normalized_database_url(self) -> str:
        if not self.database_url.startswith("sqlite:///"):
            return self.database_url

        db_path = self.database_url.replace("sqlite:///", "", 1)
        path = Path(db_path)
        if path.is_absolute():
            return self.database_url
        return f"sqlite:///{(BACKEND_DIR / path).resolve().as_posix()}"

    @staticmethod
    def _resolve_backend_path(path_value: str) -> Path:
        path = Path(path_value)
        if path.is_absolute():
            return path.resolve()
        return (BACKEND_DIR / path).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
