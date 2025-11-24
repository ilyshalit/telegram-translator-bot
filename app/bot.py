"""Bot initialization and configuration."""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from .core.config import settings
from .core.logger import get_logger, logger
from .core.database import init_storage, storage
from .core.rate_limit import rate_limiter
from .middlewares import ThrottlingMiddleware, AuthMiddleware
from .handlers import private_router, channel_router, comments_router, group_events_router, menu_router

# Initialize logger
bot_logger = get_logger(__name__)


class TranslationBot:
    """Main bot class."""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.app: Optional[web.Application] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize bot components."""
        if self._initialized:
            return
        
        bot_logger.info("Initializing Translation Bot...")
        
        # Initialize storage
        await init_storage()
        
        # Create bot instance
        self.bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Create dispatcher
        self.dp = Dispatcher()
        
        # Setup middlewares
        auth_middleware = AuthMiddleware(self.bot)
        self.dp.message.middleware(ThrottlingMiddleware())
        self.dp.message.middleware(auth_middleware)
        self.dp.callback_query.middleware(auth_middleware)
        
        # Include routers
        self.dp.include_router(private_router)
        self.dp.include_router(channel_router)
        self.dp.include_router(comments_router)
        self.dp.include_router(group_events_router)
        self.dp.include_router(menu_router)
        
        # Setup startup and shutdown handlers
        self.dp.startup.register(self._on_startup)
        self.dp.shutdown.register(self._on_shutdown)
        
        self._initialized = True
        bot_logger.info("Bot initialized successfully")
    
    async def _on_startup(self):
        """Handle bot startup."""
        bot_logger.info("Bot is starting up...")
        
        # Rate limiter cleanup task starts automatically
        
        # Get bot info
        bot_info = await self.bot.get_me()
        bot_logger.info(f"Bot started: @{bot_info.username} ({bot_info.full_name})")
        
        # Set bot commands for autocomplete
        await self._set_bot_commands()
        
        # Set webhook if in webhook mode
        if settings.mode == "webhook" and settings.webhook_url:
            webhook_url = f"{settings.webhook_url}/webhook"
            await self.bot.set_webhook(webhook_url)
            bot_logger.info(f"Webhook set to: {webhook_url}")
        else:
            # Delete webhook for polling mode to avoid conflicts
            try:
                await self.bot.delete_webhook(drop_pending_updates=True)
                bot_logger.info("Webhook deleted, using polling mode")
                # Small delay to ensure webhook is fully deleted
                await asyncio.sleep(1)
            except Exception as e:
                bot_logger.warning(f"Failed to delete webhook: {e}")
    
    async def _on_shutdown(self):
        """Handle bot shutdown."""
        bot_logger.info("Bot is shutting down...")
        
        # Stop rate limiter cleanup
        rate_limiter.stop_cleanup()
        
        # Stop polling gracefully
        if self.dp:
            try:
                await self.dp.stop_polling()
                bot_logger.info("Polling stopped")
            except Exception as e:
                bot_logger.warning(f"Error stopping polling: {e}")
        
        # Close bot session
        if self.bot:
            try:
                await self.bot.session.close()
                bot_logger.info("Bot session closed")
            except Exception as e:
                bot_logger.warning(f"Error closing bot session: {e}")
        
        bot_logger.info("Bot shutdown complete")
    
    async def _set_bot_commands(self):
        """Set bot commands for autocomplete when user types '/'."""
        # English commands (default)
        en_commands = [
            BotCommand(command="start", description="🚀 Start working with the bot"),
            BotCommand(command="menu", description="🏠 Main menu with all options"),
            BotCommand(command="help", description="❓ Get detailed help"),
            BotCommand(command="setup", description="📋 Setup instructions for channels"),
            BotCommand(command="languages", description="🌐 Change interface language"),
            BotCommand(command="my_channels", description="💬 Show my connected channel chats"),
            BotCommand(command="set_my_lang", description="🔧 Set your preferred language"),
            BotCommand(command="privacy", description="🔒 Privacy policy"),
            BotCommand(command="provider", description="⚙️ Translation provider info"),
            BotCommand(command="set_channel_langs", description="👑 [Admin] Set channel languages"),
            BotCommand(command="toggle_autotranslate", description="👑 [Admin] Toggle auto-translation"),
            BotCommand(command="stats", description="👑 [Admin] Translation statistics"),
        ]
        
        # Russian commands
        ru_commands = [
            BotCommand(command="start", description="🚀 Начать работу с ботом"),
            BotCommand(command="menu", description="🏠 Главное меню со всеми опциями"),
            BotCommand(command="help", description="❓ Получить подробную помощь"),
            BotCommand(command="setup", description="📋 Инструкции по настройке каналов"),
            BotCommand(command="languages", description="🌐 Изменить язык интерфейса"),
            BotCommand(command="my_channels", description="💬 Показать мои чаты каналов"),
            BotCommand(command="set_my_lang", description="🔧 Установить предпочитаемый язык"),
            BotCommand(command="privacy", description="🔒 Политика конфиденциальности"),
            BotCommand(command="provider", description="⚙️ Информация о провайдере переводов"),
            BotCommand(command="set_channel_langs", description="👑 [Админ] Установить языки канала"),
            BotCommand(command="toggle_autotranslate", description="👑 [Админ] Переключить автоперевод"),
            BotCommand(command="stats", description="👑 [Админ] Статистика переводов"),
        ]
        
        try:
            # Set default commands (English)
            await self.bot.set_my_commands(en_commands)
            
            # Set Russian commands for Russian language scope
            from aiogram.types import BotCommandScopeDefault
            await self.bot.set_my_commands(
                ru_commands, 
                scope=BotCommandScopeDefault(),
                language_code="ru"
            )
            
            bot_logger.info("Bot commands set successfully for both languages")
        except Exception as e:
            bot_logger.error(f"Failed to set bot commands: {e}")
    
    async def update_user_commands(self, user_id: int, user_lang: str):
        """Update bot commands for a specific user based on their language preference.
        
        Note: Telegram API limitations mean command descriptions are shown based on the user's
        Telegram interface language, not the bot's language setting. However, we try to set
        commands for all private chats with the appropriate language_code.
        """
        from aiogram.types.bot_command_scope_all_private_chats import BotCommandScopeAllPrivateChats
        
        # English commands
        en_commands = [
            BotCommand(command="start", description="🚀 Start working with the bot"),
            BotCommand(command="menu", description="🏠 Main menu with all options"),
            BotCommand(command="help", description="❓ Get detailed help"),
            BotCommand(command="setup", description="📋 Setup instructions for channels"),
            BotCommand(command="languages", description="🌐 Change interface language"),
            BotCommand(command="my_channels", description="💬 Show my connected channel chats"),
            BotCommand(command="set_my_lang", description="🔧 Set your preferred language"),
            BotCommand(command="privacy", description="🔒 Privacy policy"),
            BotCommand(command="provider", description="⚙️ Translation provider info"),
            BotCommand(command="set_channel_langs", description="👑 [Admin] Set channel languages"),
            BotCommand(command="toggle_autotranslate", description="👑 [Admin] Toggle auto-translation"),
            BotCommand(command="stats", description="👑 [Admin] Translation statistics"),
        ]
        
        # Russian commands
        ru_commands = [
            BotCommand(command="start", description="🚀 Начать работу с ботом"),
            BotCommand(command="menu", description="🏠 Главное меню со всеми опциями"),
            BotCommand(command="help", description="❓ Получить подробную помощь"),
            BotCommand(command="setup", description="📋 Инструкции по настройке каналов"),
            BotCommand(command="languages", description="🌐 Изменить язык интерфейса"),
            BotCommand(command="my_channels", description="💬 Показать мои чаты каналов"),
            BotCommand(command="set_my_lang", description="🔧 Установить предпочитаемый язык"),
            BotCommand(command="privacy", description="🔒 Политика конфиденциальности"),
            BotCommand(command="provider", description="⚙️ Информация о провайдере переводов"),
            BotCommand(command="set_channel_langs", description="👑 [Админ] Установить языки канала"),
            BotCommand(command="toggle_autotranslate", description="👑 [Админ] Переключить автоперевод"),
            BotCommand(command="stats", description="👑 [Админ] Статистика переводов"),
        ]
        
        try:
            # Select commands based on user's language preference
            commands = ru_commands if user_lang == "ru" else en_commands
            
            bot_logger.info(f"Updating commands for user {user_id} (language: {user_lang})")
            
            # Map bot language to Telegram language code
            # Note: language_code must match user's Telegram interface language for this to work
            telegram_lang_code = "ru" if user_lang == "ru" else "en"
            
            # Try to set commands for all private chats with the specified language
            # This will only work if the user's Telegram interface language matches
            scope = BotCommandScopeAllPrivateChats()
            
            try:
                await self.bot.set_my_commands(
                    commands,
                    scope=scope,
                    language_code=telegram_lang_code
                )
                bot_logger.info(f"Successfully set commands for private chats with language_code={telegram_lang_code}")
            except Exception as scope_error:
                # If language_code doesn't work, try without it
                bot_logger.warning(f"Could not set commands with language_code: {scope_error}")
                try:
                    await self.bot.set_my_commands(commands, scope=scope)
                    bot_logger.info(f"Set commands without language_code for user {user_id}")
                except Exception as e:
                    bot_logger.warning(f"Could not set commands for user {user_id}: {e}")
            
            # Log first command description for verification
            first_cmd_desc = commands[0].description if commands else "N/A"
            bot_logger.info(f"Commands updated for user {user_id} to {user_lang}. First command: {first_cmd_desc}")
            
        except Exception as e:
            bot_logger.error(f"Failed to update commands for user {user_id}: {e}", exc_info=True)
    
    async def start_polling(self):
        """Start bot in polling mode with health check server."""
        if not self._initialized:
            await self.initialize()
        
        bot_logger.info("Starting bot in polling mode...")
        
        # Start health check HTTP server for Render compatibility
        host = settings.host
        port = settings.port
        
        # Create simple HTTP server for health check
        self.app = web.Application()
        self.app.router.add_get("/health", self._health_check)
        self.app.router.add_get("/", self._root_handler)
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        bot_logger.info(f"Health check server started on http://{host}:{port}")
        
        try:
            # Small delay before starting polling to avoid conflicts with previous instance
            await asyncio.sleep(2)
            
            # Start polling with error handling for conflicts
            polling_task = asyncio.create_task(self._start_polling_with_retry())
            
            # Keep the server running
            await polling_task
        except KeyboardInterrupt:
            bot_logger.info("Received interrupt signal")
        except Exception as e:
            bot_logger.error(f"Error in polling: {e}")
            raise
        finally:
            await runner.cleanup()
            await self._cleanup()
    
    async def _start_polling_with_retry(self, max_retries: int = 3):
        """Start polling with retry logic for conflict errors."""
        from aiogram.exceptions import TelegramConflictError
        
        for attempt in range(max_retries):
            try:
                bot_logger.info(f"Starting polling (attempt {attempt + 1}/{max_retries})...")
                await self.dp.start_polling(self.bot, allowed_updates=["message", "callback_query", "chat_member"])
                break  # Success, exit retry loop
            except TelegramConflictError as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Exponential backoff: 5s, 10s, 15s
                    bot_logger.warning(
                        f"TelegramConflictError on attempt {attempt + 1}: {e}. "
                        f"Waiting {wait_time} seconds before retry..."
                    )
                    await asyncio.sleep(wait_time)
                    # Try to delete webhook again
                    try:
                        await self.bot.delete_webhook(drop_pending_updates=True)
                        await asyncio.sleep(2)
                    except Exception as webhook_error:
                        bot_logger.warning(f"Failed to delete webhook during retry: {webhook_error}")
                else:
                    bot_logger.error(f"Failed to start polling after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                bot_logger.error(f"Unexpected error during polling: {e}")
                raise
    
    async def start_webhook(self, host: str = None, port: int = None):
        """Start bot in webhook mode."""
        if not self._initialized:
            await self.initialize()
        
        host = host or settings.host
        port = port or settings.port
        
        bot_logger.info(f"Starting bot in webhook mode on {host}:{port}")
        
        # Create web application
        self.app = web.Application()
        
        # Setup webhook handler
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=self.dp,
            bot=self.bot
        )
        webhook_requests_handler.register(self.app, path="/webhook")
        
        # Add health check endpoint
        self.app.router.add_get("/health", self._health_check)
        self.app.router.add_get("/", self._root_handler)
        
        # Setup application
        setup_application(self.app, self.dp, bot=self.bot)
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        bot_logger.info(f"Webhook server started on http://{host}:{port}")
        
        try:
            # Keep the server running
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            bot_logger.info("Received interrupt signal")
        except Exception as e:
            bot_logger.error(f"Error in webhook server: {e}")
            raise
        finally:
            await runner.cleanup()
            await self._cleanup()
    
    async def _health_check(self, request):
        """Health check endpoint."""
        try:
            # Check database health
            db_healthy = await storage.health_check()
            
            # Check bot connection
            bot_healthy = False
            if self.bot:
                try:
                    await self.bot.get_me()
                    bot_healthy = True
                except Exception:
                    pass
            
            if db_healthy and bot_healthy:
                return web.json_response({
                    "status": "healthy",
                    "database": "ok",
                    "bot": "ok"
                })
            else:
                return web.json_response({
                    "status": "unhealthy",
                    "database": "ok" if db_healthy else "error",
                    "bot": "ok" if bot_healthy else "error"
                }, status=503)
                
        except Exception as e:
            bot_logger.error(f"Health check error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def _root_handler(self, request):
        """Root endpoint handler."""
        return web.json_response({
            "service": "Telegram Translation Bot",
            "status": "running",
            "mode": settings.mode
        })
    
    async def _cleanup(self):
        """Cleanup resources."""
        bot_logger.info("Cleaning up resources...")
        
        # Close database connections
        try:
            # Storage cleanup is handled automatically by aiosqlite
            pass
        except Exception as e:
            bot_logger.error(f"Error cleaning up storage: {e}")


# Global bot instance
translation_bot = TranslationBot()


@asynccontextmanager
async def lifespan(app: web.Application):
    """Application lifespan manager for webhook mode."""
    # Startup
    await translation_bot.initialize()
    yield
    # Shutdown
    await translation_bot._cleanup()


def create_app() -> web.Application:
    """Create web application for webhook mode."""
    app = web.Application()
    
    # This will be called by uvicorn or other ASGI servers
    # The actual webhook setup happens in start_webhook()
    
    return app


async def run_bot():
    """Run bot based on configuration."""
    try:
        if settings.mode == "webhook":
            await translation_bot.start_webhook()
        else:
            await translation_bot.start_polling()
    except Exception as e:
        bot_logger.error(f"Failed to run bot: {e}")
        raise

