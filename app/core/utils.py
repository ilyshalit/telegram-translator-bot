"""Utility functions for the translation bot."""

import re
import unicodedata
from typing import List, Optional, Tuple
from datetime import datetime

from .config import settings
from .logger import get_logger

logger = get_logger(__name__)


def normalize_text(text: str) -> str:
    """Normalize text for processing."""
    if not text:
        return ""
    
    # Normalize Unicode
    text = unicodedata.normalize('NFKC', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def extract_text_from_message(message) -> str:
    """Extract text content from Telegram message."""
    text_parts = []
    
    # Get main text
    if hasattr(message, 'text') and message.text:
        text_parts.append(message.text)
    
    # Get caption
    if hasattr(message, 'caption') and message.caption:
        text_parts.append(message.caption)
    
    # Join all text parts
    full_text = '\n'.join(text_parts)
    
    # Normalize and limit length
    normalized = normalize_text(full_text)
    
    if len(normalized) > settings.max_text_length:
        # Truncate at word boundary
        truncated = normalized[:settings.max_text_length]
        last_space = truncated.rfind(' ')
        if last_space > settings.max_text_length * 0.8:  # Don't cut too much
            truncated = truncated[:last_space]
        normalized = truncated + "..."
    
    return normalized


def split_long_message(text: str, max_length: int = None) -> List[str]:
    """Split long message into chunks that fit Telegram limits."""
    if max_length is None:
        max_length = settings.max_comment_length
    
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        # If paragraph itself is too long, split by sentences
        if len(paragraph) > max_length:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 2 <= max_length:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
                    
                    # If single sentence is still too long, force split
                    while len(current_chunk) > max_length:
                        split_point = max_length - 3  # Leave room for "..."
                        chunks.append(current_chunk[:split_point] + "...")
                        current_chunk = "..." + current_chunk[split_point:]
        else:
            # Check if we can add this paragraph to current chunk
            if len(current_chunk) + len(paragraph) + 2 <= max_length:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def format_translation_comment(
    translations: List, 
    source_lang: str, 
    is_edited: bool = False
) -> List[str]:
    """Format translation results into comment messages."""
    if not translations:
        return []
    
    messages = []
    current_message = ""
    
    # Header
    header_key = "translation_edited" if is_edited else "translation_header"
    
    for translation in translations:
        # Format single translation
        target_lang = translation.target_lang
        translated_text = translation.text
        
        # Create translation block
        block = f"🌐 Translation ({source_lang}→{target_lang}):\n{translated_text}\n\n"
        
        # Check if we can add this block to current message
        if len(current_message) + len(block) <= settings.max_comment_length:
            current_message += block
        else:
            # Save current message and start new one
            if current_message:
                messages.append(current_message.strip())
            current_message = block
    
    # Add remaining message
    if current_message:
        messages.append(current_message.strip())
    
    return messages


def is_bot_mentioned(message, bot_username: str) -> bool:
    """Check if bot is mentioned in message."""
    if not message.text:
        return False
    
    # Check for @username mention
    mention_pattern = f"@{bot_username.lower()}"
    return mention_pattern in message.text.lower()


def extract_command_args(text: str, command: str) -> Optional[str]:
    """Extract arguments from bot command."""
    if not text:
        return None
    
    # Pattern: /command args or /command@botname args
    pattern = rf"^/{command}(?:@\w+)?\s+(.+)$"
    match = re.match(pattern, text.strip(), re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    return None


def validate_language_list(lang_string: str) -> Tuple[bool, List[str], str]:
    """Validate comma-separated language list."""
    from .i18n import parse_language_list, get_supported_languages_list
    
    if not lang_string:
        return False, [], "Empty language list"
    
    languages = parse_language_list(lang_string)
    
    if not languages:
        return False, [], "No valid language codes found"
    
    if len(languages) > 5:  # Reasonable limit
        return False, [], "Too many languages (max 5)"
    
    return True, languages, ""


def escape_markdown(text: str) -> str:
    """Escape markdown special characters."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{hours}h"


def get_chat_type_name(chat_type: str) -> str:
    """Get human-readable chat type name."""
    type_names = {
        "private": "Private Chat",
        "group": "Group",
        "supergroup": "Supergroup",
        "channel": "Channel"
    }
    return type_names.get(chat_type, chat_type.title())


def is_admin_command(text: str) -> bool:
    """Check if text contains admin-only command."""
    if not text:
        return False
    
    admin_commands = [
        "/set_channel_langs",
        "/toggle_autotranslate", 
        "/stats"
    ]
    
    text_lower = text.lower().strip()
    
    for command in admin_commands:
        if text_lower.startswith(command):
            return True
    
    return False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_len = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_len] + ('.' + ext if ext else '')
    
    return filename


def get_user_display_name(user) -> str:
    """Get display name for user."""
    if hasattr(user, 'first_name') and user.first_name:
        name = user.first_name
        if hasattr(user, 'last_name') and user.last_name:
            name += f" {user.last_name}"
        return name
    elif hasattr(user, 'username') and user.username:
        return f"@{user.username}"
    else:
        return f"User {user.id}"


def log_message_info(message, action: str = "processing"):
    """Log message information safely."""
    chat_type = getattr(message.chat, 'type', 'unknown')
    chat_id = getattr(message.chat, 'id', 'unknown')
    user_id = getattr(message.from_user, 'id', 'unknown') if message.from_user else 'unknown'
    
    logger.info(
        f"{action.title()} message: chat_type={chat_type}, "
        f"chat_id={chat_id}, user_id={user_id}"
    )


def truncate_text_for_log(text: str, max_length: int = 100) -> str:
    """Truncate text for safe logging."""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

