"""Message handlers for the translation bot."""

from .private import router as private_router
from .channel import router as channel_router
from .comments import router as comments_router
from .new_commands import router as new_commands_router
from .group_events import router as group_events_router
from .menu import router as menu_router

__all__ = ["private_router", "channel_router", "comments_router", "new_commands_router", "group_events_router", "menu_router"]

