"""SQLite storage for bot settings and statistics."""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

import aiosqlite

from .config import settings
from .logger import get_logger
from .i18n import parse_language_list

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Database operation error."""
    pass


class Storage:
    """SQLite storage manager."""
    
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self):
        """Initialize database and create tables."""
        if self._initialized:
            return
        
        try:
            # Ensure database directory exists
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Enable foreign keys
                await db.execute("PRAGMA foreign_keys = ON")
                
                # Create tables
                await self._create_tables(db)
                await db.commit()
                
                logger.info("Database initialized successfully")
                self._initialized = True
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create database tables."""
        
        # Channel settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_settings (
                chat_id INTEGER PRIMARY KEY,
                target_langs TEXT NOT NULL DEFAULT 'en',
                autotranslate INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        
        # User settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                target_lang TEXT NOT NULL DEFAULT 'en',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        
        # Statistics table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                posts INTEGER NOT NULL DEFAULT 0,
                translations INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
        """)
        
        # User-Channel relationship table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                channel_title TEXT,
                added_at INTEGER NOT NULL,
                UNIQUE(user_id, channel_id),
                FOREIGN KEY(user_id) REFERENCES user_settings(user_id),
                FOREIGN KEY(channel_id) REFERENCES channel_settings(chat_id)
            )
        """)
        
        # Create indexes for better performance
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stats_date_channel 
            ON stats(date, channel_id)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stats_created_at 
            ON stats(created_at)
        """)
    
    async def get_channel_settings(self, chat_id: int) -> Dict[str, Any]:
        """Get channel settings."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT target_langs, autotranslate FROM channel_settings WHERE chat_id = ?",
                    (chat_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        target_langs_str, autotranslate = row
                        return {
                            "target_langs": parse_language_list(target_langs_str),
                            "autotranslate": bool(autotranslate)
                        }
                    else:
                        # Return default settings
                        return {
                            "target_langs": settings.get_default_channel_langs(),
                            "autotranslate": True
                        }
                        
        except Exception as e:
            logger.error(f"Failed to get channel settings for {chat_id}: {e}")
            raise DatabaseError(f"Failed to get channel settings: {e}")
    
    async def set_channel_settings(
        self, 
        chat_id: int, 
        target_langs: Optional[List[str]] = None,
        autotranslate: Optional[bool] = None
    ):
        """Set channel settings."""
        try:
            current_time = int(datetime.now().timestamp())
            
            async with aiosqlite.connect(self.db_path) as db:
                # Get current settings
                async with db.execute(
                    "SELECT target_langs, autotranslate FROM channel_settings WHERE chat_id = ?",
                    (chat_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                
                if row:
                    # Update existing settings
                    current_langs, current_auto = row
                    
                    new_langs = ",".join(target_langs) if target_langs else current_langs
                    new_auto = autotranslate if autotranslate is not None else bool(current_auto)
                    
                    await db.execute(
                        """UPDATE channel_settings 
                           SET target_langs = ?, autotranslate = ?, updated_at = ?
                           WHERE chat_id = ?""",
                        (new_langs, int(new_auto), current_time, chat_id)
                    )
                else:
                    # Insert new settings
                    new_langs = ",".join(target_langs) if target_langs else settings.default_channel_langs
                    new_auto = autotranslate if autotranslate is not None else True
                    
                    await db.execute(
                        """INSERT INTO channel_settings 
                           (chat_id, target_langs, autotranslate, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (chat_id, new_langs, int(new_auto), current_time, current_time)
                    )
                
                await db.commit()
                logger.info(f"Channel settings updated for {chat_id}")
                
        except Exception as e:
            logger.error(f"Failed to set channel settings for {chat_id}: {e}")
            raise DatabaseError(f"Failed to set channel settings: {e}")
    
    async def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user settings. Returns None if user not found."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT target_lang FROM user_settings WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return {"target_lang": row[0]}
                    else:
                        return None  # User not found, needs language selection
                        
        except Exception as e:
            logger.error(f"Failed to get user settings for {user_id}: {e}")
            raise DatabaseError(f"Failed to get user settings: {e}")
    
    async def set_user_settings(self, user_id: int, target_lang: str):
        """Set user settings."""
        try:
            current_time = int(datetime.now().timestamp())
            
            async with aiosqlite.connect(self.db_path) as db:
                # Check if user exists
                async with db.execute(
                    "SELECT 1 FROM user_settings WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    exists = await cursor.fetchone()
                
                if exists:
                    # Update existing settings
                    await db.execute(
                        "UPDATE user_settings SET target_lang = ?, updated_at = ? WHERE user_id = ?",
                        (target_lang, current_time, user_id)
                    )
                else:
                    # Insert new settings
                    await db.execute(
                        """INSERT INTO user_settings 
                           (user_id, target_lang, created_at, updated_at)
                           VALUES (?, ?, ?, ?)""",
                        (user_id, target_lang, current_time, current_time)
                    )
                
                await db.commit()
                logger.info(f"User settings updated for {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to set user settings for {user_id}: {e}")
            raise DatabaseError(f"Failed to set user settings: {e}")
    
    async def record_translation_stats(
        self, 
        channel_id: int, 
        posts: int = 0, 
        translations: int = 0
    ):
        """Record translation statistics."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            current_time = int(datetime.now().timestamp())
            
            async with aiosqlite.connect(self.db_path) as db:
                # Check if record exists for today
                async with db.execute(
                    "SELECT id, posts, translations FROM stats WHERE date = ? AND channel_id = ?",
                    (today, channel_id)
                ) as cursor:
                    row = await cursor.fetchone()
                
                if row:
                    # Update existing record
                    record_id, current_posts, current_translations = row
                    await db.execute(
                        "UPDATE stats SET posts = ?, translations = ? WHERE id = ?",
                        (current_posts + posts, current_translations + translations, record_id)
                    )
                else:
                    # Insert new record
                    await db.execute(
                        """INSERT INTO stats 
                           (date, channel_id, posts, translations, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (today, channel_id, posts, translations, current_time)
                    )
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to record stats for channel {channel_id}: {e}")
            # Don't raise exception for stats recording failures
    
    async def get_translation_stats(self, channel_id: int, days: int = 7) -> Dict[str, int]:
        """Get translation statistics for specified period."""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    """SELECT SUM(posts), SUM(translations) 
                       FROM stats 
                       WHERE channel_id = ? AND date >= ?""",
                    (channel_id, start_date)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                    if row and row[0] is not None:
                        return {
                            "posts": row[0] or 0,
                            "translations": row[1] or 0
                        }
                    else:
                        return {"posts": 0, "translations": 0}
                        
        except Exception as e:
            logger.error(f"Failed to get stats for channel {channel_id}: {e}")
            return {"posts": 0, "translations": 0}
    
    async def add_user_channel(self, user_id: int, channel_id: int, channel_title: str = None):
        """Add user-channel relationship."""
        try:
            current_time = int(datetime.now().timestamp())
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO user_channels 
                       (user_id, channel_id, channel_title, added_at)
                       VALUES (?, ?, ?, ?)""",
                    (user_id, channel_id, channel_title or f"Channel {channel_id}", current_time)
                )
                await db.commit()
                logger.info(f"Added user {user_id} to channel {channel_id}")
                
        except Exception as e:
            logger.error(f"Failed to add user channel relationship: {e}")
    
    async def remove_user_channel(self, user_id: int, channel_id: int):
        """Remove user-channel relationship."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM user_channels WHERE user_id = ? AND channel_id = ?",
                    (user_id, channel_id)
                )
                await db.commit()
                logger.info(f"Removed user {user_id} from channel {channel_id}")
                
        except Exception as e:
            logger.error(f"Failed to remove user channel relationship: {e}")

    async def get_user_channels(self, user_id: int) -> List[Dict[str, Any]]:
        """Get channels where user added the bot."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    """SELECT uc.channel_id, uc.channel_title, uc.added_at,
                              cs.target_langs, cs.autotranslate, cs.created_at, cs.updated_at
                       FROM user_channels uc
                       LEFT JOIN channel_settings cs ON uc.channel_id = cs.chat_id
                       WHERE uc.user_id = ?
                       ORDER BY uc.added_at DESC""",
                    (user_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                    channels = []
                    for row in rows:
                        channels.append({
                            "chat_id": row[0],
                            "title": row[1] or f"Channel {row[0]}",
                            "added_at": row[2],
                            "target_langs": row[3] or "en",
                            "autotranslate": bool(row[4]) if row[4] is not None else True,
                            "created_at": row[5],
                            "updated_at": row[6],
                        })
                    
                    return channels
                        
        except Exception as e:
            logger.error(f"Failed to get user channels for {user_id}: {e}")
            return []
    
    async def cleanup_old_stats(self, days_to_keep: int = 30):
        """Clean up old statistics records."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM stats WHERE date < ?",
                    (cutoff_date,)
                )
                deleted_count = cursor.rowcount
                await db.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old statistics records")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old stats: {e}")
    
    async def get_all_channels(self) -> List[int]:
        """Get all channels with settings."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT chat_id FROM channel_settings") as cursor:
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
                    
        except Exception as e:
            logger.error(f"Failed to get all channels: {e}")
            return []
    
    async def delete_user_data(self, user_id: int):
        """Delete all user data (GDPR compliance)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
                await db.commit()
                logger.info(f"Deleted user data for {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to delete user data for {user_id}: {e}")
            raise DatabaseError(f"Failed to delete user data: {e}")
    
    async def delete_channel_data(self, chat_id: int):
        """Delete all channel data."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM channel_settings WHERE chat_id = ?", (chat_id,))
                await db.execute("DELETE FROM stats WHERE channel_id = ?", (chat_id,))
                await db.commit()
                logger.info(f"Deleted channel data for {chat_id}")
                
        except Exception as e:
            logger.error(f"Failed to delete channel data for {chat_id}: {e}")
            raise DatabaseError(f"Failed to delete channel data: {e}")
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("SELECT 1")
                return True
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global storage instance
storage = Storage()


async def init_storage():
    """Initialize storage on startup."""
    await storage.initialize()


# Utility functions for common operations
async def get_channel_target_languages(chat_id: int) -> List[str]:
    """Get target languages for a channel."""
    settings_data = await storage.get_channel_settings(chat_id)
    return settings_data["target_langs"]


async def is_autotranslate_enabled(chat_id: int) -> bool:
    """Check if auto-translation is enabled for a channel."""
    settings_data = await storage.get_channel_settings(chat_id)
    return settings_data["autotranslate"]


async def get_user_target_language(user_id: int) -> str:
    """Get target language for a user."""
    settings_data = await storage.get_user_settings(user_id)
    return settings_data.get("target_lang", settings.default_user_lang) if settings_data else settings.default_user_lang

