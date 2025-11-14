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
from .handlers import private_router, channel_router, comments_router, new_commands_router, group_events_router, menu_router

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
        self.dp.include_router(new_commands_router)
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
            # Delete webhook for polling mode
            await self.bot.delete_webhook()
            bot_logger.info("Webhook deleted, using polling mode")
    
    async def _on_shutdown(self):
        """Handle bot shutdown."""
        bot_logger.info("Bot is shutting down...")
        
        # Stop rate limiter cleanup
        rate_limiter.stop_cleanup()
        
        # Close bot session
        if self.bot:
            await self.bot.session.close()
        
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
            BotCommand(command="my_channels", description="📺 Show my connected channels"),
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
            BotCommand(command="my_channels", description="📺 Показать мои подключенные каналы"),
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
    
    async def start_polling(self):
        """Start bot in polling mode."""
        if not self._initialized:
            await self.initialize()
        
        bot_logger.info("Starting bot in polling mode...")
        
        try:
            await self.dp.start_polling(self.bot)
        except KeyboardInterrupt:
            bot_logger.info("Received interrupt signal")
        except Exception as e:
            bot_logger.error(f"Error in polling: {e}")
            raise
        finally:
            await self._cleanup()
    
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

