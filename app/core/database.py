"""Universal database adapter for SQLite and PostgreSQL."""

import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse

import aiosqlite
try:
    import psycopg2
    import psycopg2.pool
except ImportError:
    psycopg2 = None

from .config import settings
from .logger import get_logger
from .i18n import parse_language_list

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Database operation error."""
    pass


class UniversalStorage:
    """Universal storage manager for SQLite and PostgreSQL."""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_url
        self.db_type = self._detect_db_type()
        self._initialized = False
        self._pool = None
    
    def _detect_db_type(self) -> str:
        """Detect database type from URL."""
        # For now, always use SQLite to avoid PostgreSQL complications
        # TODO: Add PostgreSQL support later
        return 'sqlite'
    
    async def initialize(self):
        """Initialize database and create tables."""
        if self._initialized:
            return
        
        try:
            if self.db_type == 'postgresql':
                await self._init_postgresql()
            else:
                await self._init_sqlite()
            
            logger.info(f"Database ({self.db_type}) initialized successfully")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
    
    async def _init_postgresql(self):
        """Initialize PostgreSQL connection."""
        if not psycopg2:
            raise DatabaseError("psycopg2 not installed for PostgreSQL support")
        
        # Parse database URL
        parsed = urlparse(self.database_url)
        
        # Create connection pool
        self._pool = await asyncpg.create_pool(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:],  # Remove leading slash
            min_size=1,
            max_size=10
        )
        
        # Create tables
        async with self._pool.acquire() as conn:
            await self._create_postgresql_tables(conn)
    
    async def _init_sqlite(self):
        """Initialize SQLite connection."""
        # Extract path from URL
        if self.database_url.startswith('sqlite:///'):
            db_path = self.database_url[10:]  # Remove 'sqlite:///'
        else:
            db_path = self.database_url
        
        self.db_path = db_path
        
        # Create database directory if needed
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
        
        # Create tables
        async with aiosqlite.connect(db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await self._create_sqlite_tables(db)
            await db.commit()
    
    async def _create_postgresql_tables(self, conn):
        """Create PostgreSQL tables."""
        
        # Channel settings table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS channel_settings (
                chat_id BIGINT PRIMARY KEY,
                target_langs TEXT NOT NULL DEFAULT 'en',
                autotranslate BOOLEAN NOT NULL DEFAULT TRUE,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL
            )
        """)
        
        # User settings table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id BIGINT PRIMARY KEY,
                target_lang TEXT NOT NULL DEFAULT 'en',
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL
            )
        """)
        
        # Statistics table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id SERIAL PRIMARY KEY,
                date TEXT NOT NULL,
                channel_id BIGINT NOT NULL,
                posts INTEGER NOT NULL DEFAULT 0,
                translations INTEGER NOT NULL DEFAULT 0,
                created_at BIGINT NOT NULL
            )
        """)
        
        # User-Channel relationship table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_channels (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                channel_title TEXT,
                added_at BIGINT NOT NULL,
                UNIQUE(user_id, channel_id)
            )
        """)
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stats_date_channel 
            ON stats(date, channel_id)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stats_created_at 
            ON stats(created_at)
        """)
    
    async def _create_sqlite_tables(self, db):
        """Create SQLite tables."""
        
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
                UNIQUE(user_id, channel_id)
            )
        """)
        
        # Create indexes
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stats_date_channel 
            ON stats(date, channel_id)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stats_created_at 
            ON stats(created_at)
        """)
    
    async def _execute_query(self, query: str, params: tuple = (), fetch: str = None):
        """Execute query with appropriate database connection."""
        if self.db_type == 'postgresql':
            async with self._pool.acquire() as conn:
                if fetch == 'one':
                    return await conn.fetchrow(query, *params)
                elif fetch == 'all':
                    return await conn.fetch(query, *params)
                else:
                    return await conn.execute(query, *params)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                if fetch == 'one':
                    async with db.execute(query, params) as cursor:
                        return await cursor.fetchone()
                elif fetch == 'all':
                    async with db.execute(query, params) as cursor:
                        return await cursor.fetchall()
                else:
                    await db.execute(query, params)
                    await db.commit()
    
    async def get_channel_settings(self, chat_id: int) -> Dict[str, Any]:
        """Get channel settings."""
        try:
            if self.db_type == 'postgresql':
                query = "SELECT target_langs, autotranslate FROM channel_settings WHERE chat_id = $1"
            else:
                query = "SELECT target_langs, autotranslate FROM channel_settings WHERE chat_id = ?"
            
            row = await self._execute_query(query, (chat_id,), fetch='one')
            
            if row:
                target_langs_str = row[0] if self.db_type == 'postgresql' else row[0]
                autotranslate = row[1] if self.db_type == 'postgresql' else bool(row[1])
                
                return {
                    "target_langs": parse_language_list(target_langs_str),
                    "autotranslate": autotranslate
                }
            else:
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
            
            # Get current settings
            if self.db_type == 'postgresql':
                query = "SELECT target_langs, autotranslate FROM channel_settings WHERE chat_id = $1"
            else:
                query = "SELECT target_langs, autotranslate FROM channel_settings WHERE chat_id = ?"
            
            row = await self._execute_query(query, (chat_id,), fetch='one')
            
            if row:
                # Update existing settings
                current_langs = row[0]
                current_auto = row[1] if self.db_type == 'postgresql' else bool(row[1])
                
                new_langs = ",".join(target_langs) if target_langs else current_langs
                new_auto = autotranslate if autotranslate is not None else current_auto
                
                if self.db_type == 'postgresql':
                    query = """UPDATE channel_settings 
                               SET target_langs = $1, autotranslate = $2, updated_at = $3
                               WHERE chat_id = $4"""
                else:
                    query = """UPDATE channel_settings 
                               SET target_langs = ?, autotranslate = ?, updated_at = ?
                               WHERE chat_id = ?"""
                
                await self._execute_query(query, (new_langs, new_auto, current_time, chat_id))
            else:
                # Insert new settings
                new_langs = ",".join(target_langs) if target_langs else settings.default_channel_langs
                new_auto = autotranslate if autotranslate is not None else True
                
                if self.db_type == 'postgresql':
                    query = """INSERT INTO channel_settings 
                               (chat_id, target_langs, autotranslate, created_at, updated_at)
                               VALUES ($1, $2, $3, $4, $5)"""
                else:
                    query = """INSERT INTO channel_settings 
                               (chat_id, target_langs, autotranslate, created_at, updated_at)
                               VALUES (?, ?, ?, ?, ?)"""
                
                await self._execute_query(query, (chat_id, new_langs, new_auto, current_time, current_time))
            
            logger.info(f"Channel settings updated for {chat_id}")
            
        except Exception as e:
            logger.error(f"Failed to set channel settings for {chat_id}: {e}")
            raise DatabaseError(f"Failed to set channel settings: {e}")
    
    async def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user settings."""
        try:
            if self.db_type == 'postgresql':
                query = "SELECT target_lang FROM user_settings WHERE user_id = $1"
            else:
                query = "SELECT target_lang FROM user_settings WHERE user_id = ?"
            
            row = await self._execute_query(query, (user_id,), fetch='one')
            
            if row:
                return {"target_lang": row[0]}
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user settings for {user_id}: {e}")
            raise DatabaseError(f"Failed to get user settings: {e}")
    
    async def set_user_settings(self, user_id: int, target_lang: str):
        """Set user settings."""
        try:
            current_time = int(datetime.now().timestamp())
            
            # Check if user exists
            if self.db_type == 'postgresql':
                query = "SELECT 1 FROM user_settings WHERE user_id = $1"
            else:
                query = "SELECT 1 FROM user_settings WHERE user_id = ?"
            
            exists = await self._execute_query(query, (user_id,), fetch='one')
            
            if exists:
                # Update existing settings
                if self.db_type == 'postgresql':
                    query = "UPDATE user_settings SET target_lang = $1, updated_at = $2 WHERE user_id = $3"
                else:
                    query = "UPDATE user_settings SET target_lang = ?, updated_at = ? WHERE user_id = ?"
                
                await self._execute_query(query, (target_lang, current_time, user_id))
            else:
                # Insert new settings
                if self.db_type == 'postgresql':
                    query = """INSERT INTO user_settings 
                               (user_id, target_lang, created_at, updated_at)
                               VALUES ($1, $2, $3, $4)"""
                else:
                    query = """INSERT INTO user_settings 
                               (user_id, target_lang, created_at, updated_at)
                               VALUES (?, ?, ?, ?)"""
                
                await self._execute_query(query, (user_id, target_lang, current_time, current_time))
            
            logger.info(f"User settings updated for {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to set user settings for {user_id}: {e}")
            raise DatabaseError(f"Failed to set user settings: {e}")
    
    async def add_user_channel(self, user_id: int, channel_id: int, channel_title: str = None):
        """Add user-channel relationship."""
        try:
            current_time = int(datetime.now().timestamp())
            
            if self.db_type == 'postgresql':
                query = """INSERT INTO user_channels 
                           (user_id, channel_id, channel_title, added_at)
                           VALUES ($1, $2, $3, $4)
                           ON CONFLICT (user_id, channel_id) 
                           DO UPDATE SET channel_title = $3, added_at = $4"""
            else:
                query = """INSERT OR REPLACE INTO user_channels 
                           (user_id, channel_id, channel_title, added_at)
                           VALUES (?, ?, ?, ?)"""
            
            await self._execute_query(query, (user_id, channel_id, channel_title or f"Channel {channel_id}", current_time))
            logger.info(f"Added user {user_id} to channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Failed to add user channel relationship: {e}")
    
    async def get_user_channels(self, user_id: int) -> List[Dict[str, Any]]:
        """Get channels where user added the bot."""
        try:
            if self.db_type == 'postgresql':
                query = """SELECT uc.channel_id, uc.channel_title, uc.added_at,
                                  cs.target_langs, cs.autotranslate, cs.created_at, cs.updated_at
                           FROM user_channels uc
                           LEFT JOIN channel_settings cs ON uc.channel_id = cs.chat_id
                           WHERE uc.user_id = $1
                           ORDER BY uc.added_at DESC"""
            else:
                query = """SELECT uc.channel_id, uc.channel_title, uc.added_at,
                                  cs.target_langs, cs.autotranslate, cs.created_at, cs.updated_at
                           FROM user_channels uc
                           LEFT JOIN channel_settings cs ON uc.channel_id = cs.chat_id
                           WHERE uc.user_id = ?
                           ORDER BY uc.added_at DESC"""
            
            rows = await self._execute_query(query, (user_id,), fetch='all')
            
            channels = []
            for row in rows:
                autotranslate = row[4] if self.db_type == 'postgresql' else bool(row[4]) if row[4] is not None else True
                
                channels.append({
                    "chat_id": row[0],
                    "title": row[1] or f"Channel {row[0]}",
                    "added_at": row[2],
                    "target_langs": row[3] or "en",
                    "autotranslate": autotranslate,
                    "created_at": row[5],
                    "updated_at": row[6],
                })
            
            return channels
            
        except Exception as e:
            logger.error(f"Failed to get user channels for {user_id}: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if self.db_type == 'postgresql':
                query = "SELECT 1"
            else:
                query = "SELECT 1"
            
            await self._execute_query(query, (), fetch='one')
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database connections."""
        if self.db_type == 'postgresql' and self._pool:
            await self._pool.close()


# Global storage instance
storage = UniversalStorage()


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

