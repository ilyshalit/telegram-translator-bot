"""Rate limiting functionality."""

import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

from .config import settings
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests: int
    window: int  # seconds
    
    def __post_init__(self):
        if self.requests <= 0:
            raise ValueError("Requests must be positive")
        if self.window <= 0:
            raise ValueError("Window must be positive")


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.buckets: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str) -> Tuple[bool, Optional[int]]:
        """Check if request is allowed for given key."""
        async with self._lock:
            current_time = time.time()
            bucket = self.buckets[key]
            
            # Remove old requests outside the window
            while bucket and bucket[0] <= current_time - self.config.window:
                bucket.popleft()
            
            # Check if we're under the limit
            if len(bucket) < self.config.requests:
                bucket.append(current_time)
                return True, None
            else:
                # Calculate when the next request will be allowed
                oldest_request = bucket[0]
                retry_after = int(oldest_request + self.config.window - current_time) + 1
                return False, retry_after
    
    async def cleanup_old_buckets(self):
        """Clean up old buckets to prevent memory leaks."""
        async with self._lock:
            current_time = time.time()
            keys_to_remove = []
            
            for key, bucket in self.buckets.items():
                # Remove old requests
                while bucket and bucket[0] <= current_time - self.config.window:
                    bucket.popleft()
                
                # If bucket is empty, mark for removal
                if not bucket:
                    keys_to_remove.append(key)
            
            # Remove empty buckets
            for key in keys_to_remove:
                del self.buckets[key]
            
            if keys_to_remove:
                logger.debug(f"Cleaned up {len(keys_to_remove)} empty rate limit buckets")


class MultiLevelRateLimiter:
    """Multi-level rate limiter for different scopes."""
    
    def __init__(self):
        # User-level rate limiting
        self.user_limiter = RateLimiter(
            RateLimitConfig(
                requests=settings.rate_limit_requests,
                window=settings.rate_limit_window
            )
        )
        
        # Chat-level rate limiting (more permissive)
        self.chat_limiter = RateLimiter(
            RateLimitConfig(
                requests=settings.rate_limit_requests * 3,  # 3x more for chats
                window=settings.rate_limit_window
            )
        )
        
        # Global rate limiting (very permissive, for DDoS protection)
        self.global_limiter = RateLimiter(
            RateLimitConfig(
                requests=1000,  # High limit for global
                window=60  # Per minute
            )
        )
        
        # Cleanup task will be started when needed
        self._cleanup_task = None
    
    async def _start_cleanup_task(self):
        """Start periodic cleanup task."""
        if self._cleanup_task is not None:
            return
            
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Clean up every 5 minutes
                    await self.user_limiter.cleanup_old_buckets()
                    await self.chat_limiter.cleanup_old_buckets()
                    await self.global_limiter.cleanup_old_buckets()
                except Exception as e:
                    logger.error(f"Rate limiter cleanup error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def check_limits(
        self, 
        user_id: int, 
        chat_id: Optional[int] = None
    ) -> Tuple[bool, Optional[int], str]:
        """
        Check all rate limits.
        
        Returns:
            (is_allowed, retry_after_seconds, limit_type)
        """
        
        # Check global limit first
        global_allowed, global_retry = await self.global_limiter.is_allowed("global")
        if not global_allowed:
            logger.warning(f"Global rate limit exceeded")
            return False, global_retry, "global"
        
        # Check user limit
        user_allowed, user_retry = await self.user_limiter.is_allowed(f"user:{user_id}")
        if not user_allowed:
            logger.info(f"User rate limit exceeded for user {user_id}")
            return False, user_retry, "user"
        
        # Check chat limit if in a chat
        if chat_id and chat_id != user_id:  # Don't double-check for private chats
            chat_allowed, chat_retry = await self.chat_limiter.is_allowed(f"chat:{chat_id}")
            if not chat_allowed:
                logger.info(f"Chat rate limit exceeded for chat {chat_id}")
                return False, chat_retry, "chat"
        
        return True, None, ""
    
    async def is_user_allowed(self, user_id: int) -> Tuple[bool, Optional[int]]:
        """Check if user is allowed (simplified interface)."""
        allowed, retry_after, _ = await self.check_limits(user_id)
        return allowed, retry_after
    
    async def is_chat_allowed(self, user_id: int, chat_id: int) -> Tuple[bool, Optional[int]]:
        """Check if user in chat is allowed (simplified interface)."""
        allowed, retry_after, _ = await self.check_limits(user_id, chat_id)
        return allowed, retry_after
    
    def stop_cleanup(self):
        """Stop cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()


# Global rate limiter instance
rate_limiter = MultiLevelRateLimiter()


# Decorator for rate limiting
def rate_limit(func):
    """Decorator to add rate limiting to handler functions."""
    async def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id if message.from_user else 0
        chat_id = message.chat.id if message.chat else user_id
        
        # Check rate limits
        allowed, retry_after, limit_type = await rate_limiter.check_limits(user_id, chat_id)
        
        if not allowed:
            # Import here to avoid circular imports
            from ..core.i18n import get_localized_string, detect_user_language
            
            # Detect user language for error message
            user_lang = detect_user_language(
                message.text or message.caption or "", 
                user_id
            )
            
            error_msg = get_localized_string("rate_limit", user_lang)
            
            try:
                await message.reply(error_msg)
            except Exception as e:
                logger.error(f"Failed to send rate limit message: {e}")
            
            return
        
        # Call original function
        return await func(message, *args, **kwargs)
    
    return wrapper


# Context manager for manual rate limiting
class RateLimitContext:
    """Context manager for manual rate limiting."""
    
    def __init__(self, user_id: int, chat_id: Optional[int] = None):
        self.user_id = user_id
        self.chat_id = chat_id
        self.allowed = False
        self.retry_after = None
        self.limit_type = ""
    
    async def __aenter__(self):
        """Check rate limits on enter."""
        self.allowed, self.retry_after, self.limit_type = await rate_limiter.check_limits(
            self.user_id, self.chat_id
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Nothing to do on exit."""
        pass
    
    @property
    def is_allowed(self) -> bool:
        """Check if request is allowed."""
        return self.allowed

