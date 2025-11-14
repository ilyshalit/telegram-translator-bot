"""Channel settings data model."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

from ..core.i18n import parse_language_list, normalize_language_code


class ChannelSettings(BaseModel):
    """Channel settings model."""
    
    chat_id: int = Field(..., description="Telegram chat ID")
    target_langs: List[str] = Field(default=["en"], description="Target languages for translation")
    autotranslate: bool = Field(default=True, description="Enable auto-translation")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    @validator("target_langs", pre=True)
    def validate_target_langs(cls, v):
        """Validate and normalize target languages."""
        if isinstance(v, str):
            # Parse comma-separated string
            languages = parse_language_list(v)
        elif isinstance(v, list):
            # Validate list of language codes
            languages = []
            for lang in v:
                normalized = normalize_language_code(lang)
                if normalized and normalized not in languages:
                    languages.append(normalized)
        else:
            languages = ["en"]  # Default fallback
        
        if not languages:
            languages = ["en"]
        
        return languages
    
    @validator("chat_id")
    def validate_chat_id(cls, v):
        """Validate chat ID."""
        if not isinstance(v, int):
            raise ValueError("Chat ID must be an integer")
        return v
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "chat_id": self.chat_id,
            "target_langs": ",".join(self.target_langs),
            "autotranslate": int(self.autotranslate),
            "created_at": int(self.created_at.timestamp()) if self.created_at else None,
            "updated_at": int(self.updated_at.timestamp()) if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChannelSettings":
        """Create instance from dictionary."""
        return cls(
            chat_id=data["chat_id"],
            target_langs=data.get("target_langs", "en"),
            autotranslate=bool(data.get("autotranslate", True)),
            created_at=datetime.fromtimestamp(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromtimestamp(data["updated_at"]) if data.get("updated_at") else None,
        )
    
    def add_language(self, lang_code: str) -> bool:
        """Add a language to target languages."""
        normalized = normalize_language_code(lang_code)
        if normalized and normalized not in self.target_langs:
            self.target_langs.append(normalized)
            self.updated_at = datetime.now()
            return True
        return False
    
    def remove_language(self, lang_code: str) -> bool:
        """Remove a language from target languages."""
        normalized = normalize_language_code(lang_code)
        if normalized and normalized in self.target_langs and len(self.target_langs) > 1:
            self.target_langs.remove(normalized)
            self.updated_at = datetime.now()
            return True
        return False
    
    def has_language(self, lang_code: str) -> bool:
        """Check if language is in target languages."""
        normalized = normalize_language_code(lang_code)
        return normalized in self.target_langs if normalized else False
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

