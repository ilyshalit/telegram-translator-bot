#!/usr/bin/env python3
"""
Скрипт для сброса webhook и чистого запуска бота.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from aiogram import Bot


async def reset_webhook():
    """Reset webhook and clear any conflicts."""
    print("🔄 Сброс webhook и очистка конфликтов...")
    
    if not settings.bot_token:
        print("❌ Ошибка: BOT_TOKEN не установлен!")
        return False
    
    bot = Bot(token=settings.bot_token)
    
    try:
        # Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Подключение к боту: @{bot_info.username}")
        
        # Delete webhook
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook удален, pending updates очищены")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Check webhook status
        webhook_info = await bot.get_webhook_info()
        print(f"📊 Webhook URL: {webhook_info.url or 'None'}")
        print(f"📊 Pending updates: {webhook_info.pending_update_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сброса webhook: {e}")
        return False
    
    finally:
        await bot.session.close()


async def main():
    """Main function."""
    print("🚀 Сброс и перезапуск бота...\n")
    
    success = await reset_webhook()
    
    if success:
        print("\n✅ Webhook сброшен успешно!")
        print("🔄 Запускаем бота...")
        
        # Import and run bot
        from app.main import main as bot_main
        await bot_main()
    else:
        print("\n❌ Не удалось сбросить webhook")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")




