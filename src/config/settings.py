from pydantic_settings import BaseSettings
from pydantic import Field, BaseModel
from typing import List


class SectionAliases(BaseModel):
    main_literature: list[str] = [
        "Основная литература",
        "Перечень основной литературы"
    ]
    additional_literature: list[str] = [
        "Дополнительная литература",
        "Перечень дополнительной литературы"
    ]
    material_resources: list[str] = [
        "Материально-техническое обеспечение",
        "Материально-техническая база",
        "Описание материально-технической базы",
        "МАТЕРИАЛЬНО-ТЕХНИЧЕСКОЕ И УЧЕБНО-МЕТОДИЧЕСКОЕ ОБЕСПЕЧЕНИЕ ДИСЦИПЛИНЫ",
        "Описание материально-технической базы дисциплины"
    ]


class Settings(BaseSettings):
    section_aliases: SectionAliases = Field(default_factory=SectionAliases)
    default_output_dir: str = "./output"
    single_workbook_export: bool = True
    log_level: str = "INFO"
    worker_capacity: int = 1000
    max_workers: int = 4
    alert_error_threshold: int = 5
    alert_error_window_minutes: int = 10
    extractor_version: str = "1.0.0"
    confidence_threshold: float = 0.7
    checkpoint_dir: str = "./checkpoints"
    fuzzy_deduplication_threshold: int = 85
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings():
    global _settings
    _settings = None
