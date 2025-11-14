"""Throttling middleware for rate limiting."""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from ..core.rate_limit import rate_limiter
from ..core.logger import get_logger
from ..core.i18n import get_localized_string, detect_user_language

logger = get_logger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware for rate limiting requests."""
    
    def __init__(self):
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process middleware."""
        
        # Only apply throttling to messages
        if not isinstance(event, Message):
            return await handler(event, data)
        
        message = event
        
        # Skip if no user (shouldn't happen, but be safe)
        if not message.from_user:
            return await handler(event, data)
        
        user_id = message.from_user.id
        chat_id = message.chat.id if message.chat else user_id
        
        # Check rate limits
        allowed, retry_after, limit_type = await rate_limiter.check_limits(user_id, chat_id)
        
        if not allowed:
            # Log rate limit hit
            logger.warning(
                f"Rate limit exceeded: user_id={user_id}, chat_id={chat_id}, "
                f"limit_type={limit_type}, retry_after={retry_after}"
            )
            
            # Detect user language for error message
            user_lang = detect_user_language(
                message.text or message.caption or "", 
                user_id
            )
            
            # Get localized error message
            error_msg = get_localized_string("rate_limit", user_lang)
            
            # Add retry information if available
            if retry_after:
                if user_lang == "ru":
                    error_msg += f"\n\nПовторите попытку через {retry_after} секунд."
                else:
                    error_msg += f"\n\nTry again in {retry_after} seconds."
            
            try:
                await message.reply(error_msg)
            except Exception as e:
                logger.error(f"Failed to send rate limit message: {e}")
            
            # Don't continue processing
            return
        
        # Continue with handler
        return await handler(event, data)

