"""New command handlers for enhanced bot functionality."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError

from ..core.logger import get_logger
from ..core.i18n import (
    get_localized_string, 
    detect_user_language,
    get_supported_languages_list
)
from ..core.utils import log_message_info

logger = get_logger(__name__)
router = Router()


@router.callback_query(F.data == "setup_guide")
async def setup_guide_callback(callback: CallbackQuery):
    """Handle setup guide button."""
    user_id = callback.from_user.id
    user_lang = detect_user_language("", user_id)
    
    # Get bot username
    bot_username = (await callback.bot.get_me()).username
    
    # Get setup instructions
    instructions = get_localized_string("setup_instructions", user_lang, username=bot_username)
    
    try:
        await callback.message.reply(instructions, parse_mode="Markdown")
        await callback.answer()
        logger.info(f"Sent setup guide to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send setup guide: {e}")
        await callback.answer("Error sending guide")


@router.message(Command("commands"))
async def commands_list(message: Message):
    """Handle /commands - show all available commands."""
    log_message_info(message, "commands list")
    
    user_id = message.from_user.id
    user_lang = detect_user_language(message.text or "", user_id)
    
    if user_lang == "ru":
        commands_text = """📋 **Доступные команды:**

**Основные команды:**
/start - Начать работу с ботом
/menu - Главное меню с кнопками
/help - Подробная справка
/setup - Инструкция по настройке
/languages - Выбор языка интерфейса
/my_channels - Мои подключенные каналы
/commands - Показать все команды

**Настройки:**
/set_my_lang <код> - Установить ваш язык (например: /set_my_lang ru)
/privacy - Политика конфиденциальности
/provider - Информация о провайдере переводов

**Команды для админов каналов:**
/set_channel_langs <список> - Установить языки канала (например: /set_channel_langs en,ru)
/toggle_autotranslate on|off - Включить/выключить автоперевод
/stats - Статистика переводов

**Использование:**
• В ЛС: просто отправьте текст для перевода
• В канале: бот автоматически переводит посты
• В комментариях: упомяните бота @{username} или ответьте на его сообщение"""
    else:
        commands_text = """📋 **Available Commands:**

**Main Commands:**
/start - Start working with the bot
/menu - Main menu with buttons
/help - Detailed help
/setup - Setup instructions
/languages - Interface language selection
/my_channels - My connected channels
/commands - Show all commands

**Settings:**
/set_my_lang <code> - Set your language (example: /set_my_lang en)
/privacy - Privacy policy
/provider - Translation provider info

**Channel Admin Commands:**
/set_channel_langs <list> - Set channel languages (example: /set_channel_langs en,ru)
/toggle_autotranslate on|off - Enable/disable auto-translation
/stats - Translation statistics

**Usage:**
• In PM: just send text to translate
• In channel: bot automatically translates posts
• In comments: mention bot @{username} or reply to its message"""
    
    # Get bot username
    bot_username = (await message.bot.get_me()).username
    formatted_text = commands_text.format(username=bot_username)
    
    try:
        await message.reply(formatted_text, parse_mode="Markdown")
        logger.info(f"Sent commands list to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send commands list: {e}")
