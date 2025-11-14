"""Authentication and authorization middleware."""

import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from ..core.logger import get_logger
from ..core.utils import is_admin_command
from ..core.i18n import get_localized_string, detect_user_language

logger = get_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware for authentication and authorization."""
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._admin_cache = {}  # Cache admin status to reduce API calls
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process middleware."""
        
        # Only process messages and callback queries
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)
        
        # Get message from event
        if isinstance(event, CallbackQuery):
            message = event.message
        else:
            message = event
        
        # Skip if no user or message
        if not message or not message.from_user:
            return await handler(event, data)
        
        user_id = message.from_user.id
        chat_id = message.chat.id if message.chat else user_id
        
        # Add user and chat info to data
        data["user_id"] = user_id
        data["chat_id"] = chat_id
        data["is_private"] = message.chat.type == "private"
        data["is_group"] = message.chat.type in ["group", "supergroup"]
        data["is_channel"] = message.chat.type == "channel"
        
        # Check if this is an admin command
        text = message.text or message.caption or ""
        if is_admin_command(text):
            # Check admin permissions
            is_admin = await self._check_admin_permissions(user_id, chat_id, message)
            data["is_admin"] = is_admin
            
            if not is_admin:
                # Send error message
                user_lang = detect_user_language(text, user_id)
                error_msg = get_localized_string("admin_only", user_lang)
                
                try:
                    await message.reply(error_msg)
                except Exception as e:
                    logger.error(f"Failed to send admin error message: {e}")
                
                # Don't continue processing
                return
        else:
            # For non-admin commands, still check if user is admin (for context)
            if not data.get("is_private", False):
                data["is_admin"] = await self._check_admin_permissions(
                    user_id, chat_id, message, silent=True
                )
            else:
                data["is_admin"] = False
        
        # Continue with handler
        return await handler(event, data)
    
    async def _check_admin_permissions(
        self, 
        user_id: int, 
        chat_id: int, 
        message: Message,
        silent: bool = False
    ) -> bool:
        """Check if user has admin permissions in chat."""
        
        # Private chats don't have admins
        if message.chat.type == "private":
            return False
        
        # Check cache first (valid for 5 minutes)
        cache_key = f"{user_id}:{chat_id}"
        cached_result = self._admin_cache.get(cache_key)
        
        if cached_result:
            timestamp, is_admin = cached_result
            if timestamp > message.date.timestamp() - 300:  # 5 minutes
                return is_admin
        
        try:
            # Get chat member info
            member = await self.bot.get_chat_member(chat_id, user_id)
            
            # Check if user is admin or creator
            is_admin = member.status in ["administrator", "creator"]
            
            # Cache result
            self._admin_cache[cache_key] = (message.date.timestamp(), is_admin)
            
            return is_admin
            
        except TelegramBadRequest as e:
            if not silent:
                logger.warning(f"Failed to check admin status for user {user_id} in chat {chat_id}: {e}")
            return False
        except Exception as e:
            if not silent:
                logger.error(f"Unexpected error checking admin status: {e}")
            return False
    
    async def check_bot_permissions(self, chat_id: int) -> Dict[str, bool]:
        """Check bot's permissions in a chat."""
        try:
            bot_member = await self.bot.get_chat_member(chat_id, self.bot.id)
            
            permissions = {
                "can_post_messages": getattr(bot_member, "can_post_messages", False),
                "can_edit_messages": getattr(bot_member, "can_edit_messages", False),
                "can_delete_messages": getattr(bot_member, "can_delete_messages", False),
                "can_send_messages": getattr(bot_member, "can_send_messages", True),
                "is_admin": bot_member.status in ["administrator", "creator"],
            }
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to check bot permissions in chat {chat_id}: {e}")
            return {
                "can_post_messages": False,
                "can_edit_messages": False,
                "can_delete_messages": False,
                "can_send_messages": False,
                "is_admin": False,
            }
    
    def clear_admin_cache(self, user_id: int = None, chat_id: int = None):
        """Clear admin cache for specific user/chat or all."""
        if user_id and chat_id:
            cache_key = f"{user_id}:{chat_id}"
            self._admin_cache.pop(cache_key, None)
        else:
            self._admin_cache.clear()
    
    async def cleanup_cache(self):
        """Clean up old cache entries."""
        current_time = time.time()
        keys_to_remove = []
        
        for key, (timestamp, _) in self._admin_cache.items():
            if current_time - timestamp > 600:  # 10 minutes
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._admin_cache[key]
        
        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} old admin cache entries")
