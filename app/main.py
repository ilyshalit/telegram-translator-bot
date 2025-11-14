"""Main entry point for the Translation Bot."""

import asyncio
import signal
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.core.logger import logger
from app.bot import run_bot


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # The actual cleanup will be handled by the bot's shutdown handlers
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main function."""
    logger.info("Starting Telegram Translation Bot...")
    logger.info(f"Mode: {settings.mode}")
    logger.info(f"Provider: {settings.translator_provider}")
    logger.info(f"Log level: {settings.log_level}")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    try:
        # Initialize Sentry if configured
        if settings.use_sentry and settings.sentry_dsn:
            try:
                import sentry_sdk
                sentry_sdk.init(
                    dsn=settings.sentry_dsn,
                    traces_sample_rate=0.1,
                    environment="production" if settings.mode == "webhook" else "development"
                )
                logger.info("Sentry initialized")
            except ImportError:
                logger.warning("Sentry SDK not installed, skipping Sentry initialization")
            except Exception as e:
                logger.error(f"Failed to initialize Sentry: {e}")
        
        # Run the bot
        await run_bot()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)

