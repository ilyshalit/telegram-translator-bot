"""Configuration management using Pydantic Settings."""

import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Bot configuration
    bot_token: str = Field(..., env="BOT_TOKEN", description="Telegram Bot Token")
    
    # Translation provider settings
    translator_provider: str = Field("DEEPL", env="TRANSLATOR_PROVIDER", description="Translation provider")
    
    # DeepL settings
    deepl_api_key: Optional[str] = Field(None, env="DEEPL_API_KEY")
    
    # Google Translate settings
    google_project_id: Optional[str] = Field(None, env="GOOGLE_PROJECT_ID")
    google_credentials_json_path: Optional[str] = Field(None, env="GOOGLE_CREDENTIALS_JSON_PATH")
    
    # LibreTranslate settings
    libre_base_url: Optional[str] = Field(None, env="LIBRE_BASE_URL")
    libre_api_key: Optional[str] = Field(None, env="LIBRE_API_KEY")
    
    # Default language settings
    default_channel_langs: str = Field("en", env="DEFAULT_CHANNEL_LANGS")
    default_user_lang: str = Field("en", env="DEFAULT_USER_LANG")
    
    # Sentry configuration
    use_sentry: bool = Field(False, env="USE_SENTRY")
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    
    # Server configuration
    mode: str = Field("polling", env="MODE", description="Bot mode: polling or webhook")
    webhook_url: Optional[str] = Field(None, env="WEBHOOK_URL")
    port: int = Field(8080, env="PORT")
    host: str = Field("0.0.0.0", env="HOST")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field("sqlite:///bot.db", env="DATABASE_URL")
    
    # Rate limiting
    rate_limit_requests: int = Field(5, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(15, env="RATE_LIMIT_WINDOW")
    
    # Text processing limits
    max_text_length: int = Field(4096, env="MAX_TEXT_LENGTH")
    max_comment_length: int = Field(3500, env="MAX_COMMENT_LENGTH")
    
    @validator("translator_provider")
    def validate_translator_provider(cls, v):
        """Validate translator provider."""
        allowed_providers = ["DEEPL", "GOOGLE", "LIBRE", "MYMEMORY"]
        if v.upper() not in allowed_providers:
            raise ValueError(f"Translator provider must be one of: {allowed_providers}")
        return v.upper()
    
    @validator("mode")
    def validate_mode(cls, v):
        """Validate bot mode."""
        allowed_modes = ["polling", "webhook"]
        if v.lower() not in allowed_modes:
            raise ValueError(f"Mode must be one of: {allowed_modes}")
        return v.lower()
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v.upper()
    
    def get_default_channel_langs(self) -> List[str]:
        """Get default channel languages as a list."""
        return [lang.strip() for lang in self.default_channel_langs.split(",") if lang.strip()]
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
