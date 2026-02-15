"""Comment/discussion group handlers.

Bot only translates channel posts and posts translation as a comment under the post (see channel.py).
It does not reply to user messages, mentions, or replies in the discussion group.
"""

from aiogram import Router

router = Router()

# No handlers: we do not translate on user request or reply to people in the group.
# Channel post copy (from 777000) is handled in channel.py and one comment is posted there.
