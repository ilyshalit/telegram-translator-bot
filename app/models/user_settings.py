"""User settings data model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator

from ..core.i18n import normalize_language_code


class UserSettings(BaseModel):
    """User settings model."""
    
    user_id: int = Field(..., description="Telegram user ID")
    target_lang: str = Field(default="en", description="Preferred target language")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    @validator("target_lang")
    def validate_target_lang(cls, v):
        """Validate and normalize target language."""
        normalized = normalize_language_code(v)
        if not normalized:
            return "en"  # Default fallback
        return normalized
    
    @validator("user_id")
    def validate_user_id(cls, v):
        """Validate user ID."""
        if not isinstance(v, int) or v <= 0:
            raise ValueError("User ID must be a positive integer")
        return v
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "user_id": self.user_id,
            "target_lang": self.target_lang,
            "created_at": int(self.created_at.timestamp()) if self.created_at else None,
            "updated_at": int(self.updated_at.timestamp()) if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserSettings":
        """Create instance from dictionary."""
        return cls(
            user_id=data["user_id"],
            target_lang=data.get("target_lang", "en"),
            created_at=datetime.fromtimestamp(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromtimestamp(data["updated_at"]) if data.get("updated_at") else None,
        )
    
    def update_language(self, lang_code: str) -> bool:
        """Update target language."""
        normalized = normalize_language_code(lang_code)
        if normalized and normalized != self.target_lang:
            self.target_lang = normalized
            self.updated_at = datetime.now()
            return True
        return False
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

