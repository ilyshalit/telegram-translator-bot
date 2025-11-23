"""Private chat handlers for commands and translations."""

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.exceptions import TelegramAPIError

from ..core.logger import get_logger
from ..core.translate import translation_service, TranslationError
from ..core.database import storage
from ..core.i18n import (
    get_localized_string, 
    detect_user_language, 
    normalize_language_code,
    get_supported_languages_list,
    extract_language_from_text,
    get_language_name
)
from ..core.utils import (
    extract_text_from_message, 
    extract_command_args,
    validate_language_list,
    log_message_info,
    truncate_text_for_log
)
from ..core.config import settings

logger = get_logger(__name__)
router = Router()


@router.message(CommandStart())
async def start_command(message: Message):
    """Handle /start command with language selection."""
    log_message_info(message, "start command")
    
    user_id = message.from_user.id
    
    # Check if user already has language preference
    user_settings = await storage.get_user_settings(user_id)
    if user_settings:
        # User already has language, show normal start message
        user_lang = user_settings.get("target_lang", "en")
        
        # Update bot commands for this user to match their language
        try:
            from ..bot import translation_bot
            await translation_bot.update_user_commands(user_id, user_lang)
        except Exception as e:
            logger.warning(f"Failed to update commands for user {user_id}: {e}")
        
        bot_username = (await message.bot.get_me()).username
        
        start_text = get_localized_string("start_message", user_lang)
        languages_text = get_localized_string("supported_languages", user_lang)
        
        full_message = f"{start_text}\n\n{languages_text}"
        
        add_to_chat_text = get_localized_string("add_to_group", user_lang)
        menu_button_text = "🏠 Main Menu" if user_lang == "en" else "🏠 Главное меню"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=add_to_chat_text,
                    url=f"https://t.me/{bot_username}?startgroup=true"
                )
            ],
            [InlineKeyboardButton(
                text=menu_button_text,
                callback_data="show_main_menu"
            )]
        ])
        
        try:
            await message.answer(full_message, reply_markup=keyboard, parse_mode="Markdown")
            logger.info(f"Sent start message to user {user_id}")
        except TelegramAPIError as e:
            logger.error(f"Failed to send start message: {e}")
    else:
        # First time user, show language selection
        welcome_text = """🐟 **Welcome to Translation Bot!**
**Добро пожаловать в бот-переводчик!**

🌐 This bot helps translate messages in channels and groups.
🌐 Этот бот помогает переводить сообщения в каналах и группах.

**Please choose your interface language:**
**Пожалуйста, выберите язык интерфейса:**"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇸 English", callback_data="set_lang_en"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")
            ]
        ])
        
        try:
            await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
            logger.info(f"Sent language selection to user {user_id}")
        except TelegramAPIError as e:
            logger.error(f"Failed to send language selection: {e}")


@router.callback_query(F.data.startswith("set_lang_"))
async def language_selection_callback(callback_query: CallbackQuery):
    """Handle language selection callback."""
    user_id = callback_query.from_user.id
    selected_lang = callback_query.data.split("_")[-1]  # Extract 'en' or 'ru'
    
    try:
        # Save user language preference
        await storage.set_user_settings(user_id, selected_lang)
        
        # Update bot commands for this user
        from ..bot import translation_bot
        await translation_bot.update_user_commands(user_id, selected_lang)
        
        # Get bot username
        bot_username = (await callback_query.bot.get_me()).username
        
        # Show start message in selected language
        start_text = get_localized_string("start_message", selected_lang)
        languages_text = get_localized_string("supported_languages", selected_lang)
        
        full_message = f"{start_text}\n\n{languages_text}"
        
        add_to_chat_text = get_localized_string("add_to_group", selected_lang)
        menu_button_text = "🏠 Main Menu" if selected_lang == "en" else "🏠 Главное меню"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=add_to_chat_text,
                    url=f"https://t.me/{bot_username}?startgroup=true"
                )
            ],
            [InlineKeyboardButton(
                text=menu_button_text,
                callback_data="show_main_menu"
            )]
        ])
        
        await callback_query.message.edit_text(full_message, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer()
        
        logger.info(f"Set language {selected_lang} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to set language via callback: {e}")
        await callback_query.answer("Error setting language / Ошибка установки языка")


@router.callback_query(F.data == "show_main_menu")
async def show_main_menu_callback(callback_query: CallbackQuery):
    """Handle show main menu callback."""
    from .menu import create_main_menu_keyboard
    
    user_id = callback_query.from_user.id
    
    # Get user's interface language
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    menu_text = get_localized_string("main_menu", user_lang)
    keyboard = create_main_menu_keyboard(user_lang)
    
    try:
        await callback_query.message.edit_text(menu_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer()
        logger.info(f"Showed main menu to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to show main menu: {e}")


@router.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command."""
    log_message_info(message, "help command")
    
    user_id = message.from_user.id
    
    # Get user's language from database settings
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    # Get bot username for help message
    bot_username = (await message.bot.get_me()).username
    
    # Get supported languages list
    languages_list = get_supported_languages_list(user_lang)
    
    help_text = get_localized_string(
        "help_message", 
        user_lang,
        username=bot_username,
        languages=languages_list
    )
    
    try:
        await message.reply(help_text, parse_mode="Markdown")
        logger.info(f"Sent help message to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send help message: {e}")


@router.message(Command("set_my_lang"))
async def set_language_command(message: Message):
    """Handle /set_my_lang command."""
    log_message_info(message, "set language command")
    
    user_id = message.from_user.id
    
    # Get user's language from database settings
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    # Extract language code from command
    lang_arg = extract_command_args(message.text, "set_my_lang")
    
    if not lang_arg:
        from ..core.i18n import SupportedLanguage
        supported_langs = ", ".join([lang.value for lang in SupportedLanguage])
        error_text = get_localized_string("invalid_language", user_lang, languages=supported_langs)
        
        try:
            await message.reply(error_text)
        except TelegramAPIError as e:
            logger.error(f"Failed to send language error: {e}")
        return
    
    # Normalize language code
    normalized_lang = normalize_language_code(lang_arg)
    
    if not normalized_lang:
        from ..core.i18n import SupportedLanguage
        supported_langs = ", ".join([lang.value for lang in SupportedLanguage])
        error_text = get_localized_string("invalid_language", user_lang, languages=supported_langs)
        
        try:
            await message.reply(error_text)
        except TelegramAPIError as e:
            logger.error(f"Failed to send language error: {e}")
        return
    
    # Save user language preference
    try:
        await storage.set_user_settings(user_id, normalized_lang)
        
        # Update bot commands for this user
        from ..bot import translation_bot
        await translation_bot.update_user_commands(user_id, normalized_lang)
        
        # Get language name for confirmation
        lang_name = get_language_name(normalized_lang, user_lang)
        
        success_text = get_localized_string(
            "language_set", 
            user_lang,
            language=lang_name
        )
        
        await message.reply(success_text)
        logger.info(f"Set language {normalized_lang} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to set user language: {e}")
        error_text = get_localized_string("translation_error", user_lang)
        try:
            await message.reply(error_text)
        except TelegramAPIError:
            pass


@router.message(Command("privacy"))
async def privacy_command(message: Message):
    """Handle /privacy command."""
    log_message_info(message, "privacy command")
    
    user_id = message.from_user.id
    
    # Get user's language from database settings
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    privacy_text = get_localized_string("privacy_message", user_lang)
    
    try:
        await message.reply(privacy_text, parse_mode="Markdown")
        logger.info(f"Sent privacy message to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send privacy message: {e}")


@router.message(Command("provider"))
async def provider_command(message: Message):
    """Handle /provider command."""
    log_message_info(message, "provider command")
    
    user_id = message.from_user.id
    
    # Get user's language from database settings
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    provider_text = get_localized_string(
        "provider_info", 
        user_lang,
        provider=settings.translator_provider
    )
    
    try:
        await message.reply(provider_text)
        logger.info(f"Sent provider info to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send provider info: {e}")


@router.message(Command("menu"))
async def menu_command_private(message: Message):
    """Handle /menu command in private chat."""
    from .menu import create_main_menu_keyboard
    
    log_message_info(message, "menu command")
    
    user_id = message.from_user.id
    
    # Get user's interface language
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    menu_text = get_localized_string("main_menu", user_lang)
    keyboard = create_main_menu_keyboard(user_lang)
    
    try:
        await message.reply(menu_text, reply_markup=keyboard, parse_mode="Markdown")
        logger.info(f"Sent main menu to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send main menu: {e}")


@router.message(Command("setup"))
async def setup_command_private(message: Message):
    """Handle /setup command in private chat."""
    log_message_info(message, "setup command")
    
    user_id = message.from_user.id
    
    # Get user's language from database settings
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    # Get bot username
    bot_username = (await message.bot.get_me()).username
    setup_text = get_localized_string("setup_instructions", user_lang, username=bot_username)
    
    try:
        await message.reply(setup_text, parse_mode="Markdown")
        logger.info(f"Sent setup instructions to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send setup instructions: {e}")


@router.message(Command("languages"))
async def languages_command_private(message: Message):
    """Handle /languages command - show language selection buttons with current language."""
    log_message_info(message, "languages command")

    user_id = message.from_user.id
    
    # Get current user language for the message
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    # Get current language name
    current_lang_name = get_language_name(user_lang, user_lang)
    
    # Create message with current language info
    if user_lang == "ru":
        welcome_text = f"🌐 **Выбор языка интерфейса**\n\n✅ **Текущий язык:** {current_lang_name}\n\nВыберите новый язык для сообщений бота:"
    else:
        welcome_text = f"🌐 **Interface Language Selection**\n\n✅ **Current language:** {current_lang_name}\n\nSelect a new language for bot messages:"
    
    # Create keyboard with current language marked
    en_text = "🇺🇸 English" + (" ✅" if user_lang == "en" else "")
    ru_text = "🇷🇺 Русский" + (" ✅" if user_lang == "ru" else "")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=en_text, callback_data="set_lang_en"),
            InlineKeyboardButton(text=ru_text, callback_data="set_lang_ru")
        ]
    ])
    
    try:
        await message.reply(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
        logger.info(f"Sent language selection to user {user_id} via /languages command (current: {user_lang})")
    except TelegramAPIError as e:
        logger.error(f"Failed to send language selection via /languages command: {e}")


@router.message(F.chat.type == "private", ~F.text.startswith("/"))
async def translate_private_message(message: Message):
    """Handle text messages in private chat for translation."""
    log_message_info(message, "private translation")
    
    user_id = message.from_user.id
    
    # Extract text from message
    text = extract_text_from_message(message)
    
    if not text:
        user_lang = detect_user_language("", user_id)
        error_text = get_localized_string("no_text", user_lang)
        try:
            await message.reply(error_text)
        except TelegramAPIError as e:
            logger.error(f"Failed to send no text error: {e}")
        return
    
    logger.info(f"Processing translation request: {truncate_text_for_log(text)}")
    
    try:
        # Check if user specified target language in text
        target_lang, clean_text = extract_language_from_text(text)
        
        if not target_lang:
            # Get user's preferred language
            user_settings = await storage.get_user_settings(user_id)
            target_lang = user_settings.get("target_lang", "en") if user_settings else "en"
        
        if clean_text != text:
            text = clean_text  # Use cleaned text if language was extracted
        
        # Detect source language
        source_lang = await translation_service.detect_language(text)
        
        # Check if translation is needed
        if source_lang == target_lang:
            user_lang = detect_user_language(text, user_id)
            same_lang_text = get_localized_string("same_language", user_lang)
            try:
                await message.reply(same_lang_text)
            except TelegramAPIError as e:
                logger.error(f"Failed to send same language message: {e}")
            return
        
        # Perform translation
        result = await translation_service.translate(text, target_lang, source_lang)
        
        # Format response
        source_name = get_language_name(result.source_lang)
        target_name = get_language_name(result.target_lang)
        
        response = f"🌐 {source_name} → {target_name}:\n\n{result.text}"
        
        # Add provider info if requested
        if len(text) > 500:  # For longer texts, show provider
            response += f"\n\n_via {result.provider}_"
        
        await message.reply(response, parse_mode="Markdown")
        
        logger.info(
            f"Translation completed: {result.source_lang}→{result.target_lang} "
            f"via {result.provider}"
        )
        
    except TranslationError as e:
        logger.warning(f"Translation failed: {e}")
        user_lang = detect_user_language(text, user_id)
        error_text = get_localized_string("translation_error", user_lang)
        try:
            await message.reply(error_text)
        except TelegramAPIError:
            pass
    
    except Exception as e:
        logger.error(f"Unexpected error in private translation: {e}")
        user_lang = detect_user_language(text, user_id)
        error_text = get_localized_string("translation_error", user_lang)
        try:
            await message.reply(error_text)
        except TelegramAPIError:
            pass


# Admin commands for private chats (for testing/debugging)
@router.message(Command("debug_stats"))
async def debug_stats_command(message: Message):
    """Debug command to show translation stats."""
    user_id = message.from_user.id
    
    # Only allow for specific admin users (you can configure this)
    # For now, just log the request
    logger.info(f"Debug stats requested by user {user_id}")
    
    try:
        # Get available providers
        providers = translation_service.get_available_providers()
        
        response = f"🔧 **Debug Info**\n\n"
        response += f"**Available Providers:** {', '.join(providers)}\n"
        response += f"**Primary Provider:** {settings.translator_provider}\n"
        response += f"**Rate Limit:** {settings.rate_limit_requests}/{settings.rate_limit_window}s\n"
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Debug stats error: {e}")
        await message.reply("Debug info unavailable")


@router.message(Command("my_channels"))
async def my_channels_command(message: Message):
    """Handle /my_channels command - show user's connected channels."""
    log_message_info(message, "my_channels command")
    
    user_id = message.from_user.id
    
    # Get user's interface language
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    try:
        # Get user's channels from database
        channels = await storage.get_user_channels(user_id)
        
        if not channels:
            # No channels connected
            if user_lang == "ru":
                response = """💬 **Мои чаты каналов**

❌ У вас пока нет подключенных чатов каналов.

**Как подключить чат канала:**
1. Добавьте бота в группу обсуждений вашего канала (чат)
2. Убедитесь, что у вашего канала включена группа обсуждений
3. Используйте команду /setup для получения инструкций
4. Ваши чаты каналов появятся здесь автоматически

💡 **Подсказка:** Бот работает только в группах обсуждений каналов (секция комментариев)."""
            else:
                response = """💬 **My Channel Chats**

❌ You don't have any connected channel chats yet.

**How to connect a channel chat:**
1. Add the bot to your channel's discussion group (chat)
2. Make sure your channel has a discussion group enabled
3. Use /setup command for detailed instructions
4. Your channel chats will appear here automatically

💡 **Tip:** Bot only works in channel discussion groups (comments section)."""
        else:
            # Show connected channels
            if user_lang == "ru":
                response = f"💬 **Мои подключенные чаты каналов** ({len(channels)}):\n\n"
            else:
                response = f"💬 **My Connected Channel Chats** ({len(channels)}):\n\n"
            
            for i, channel in enumerate(channels, 1):
                channel_name = channel.get('title', f'Channel {channel["chat_id"]}')
                target_langs = channel.get('target_langs', 'en')
                if isinstance(target_langs, str):
                    target_langs = target_langs.split(',')
                autotranslate = channel.get('autotranslate', True)
                
                status_emoji = "✅" if autotranslate else "⏸️"
                langs_text = ", ".join(target_langs)
                
                # Format added date
                added_at = channel.get('added_at')
                if added_at:
                    from datetime import datetime
                    added_date = datetime.fromtimestamp(added_at).strftime("%d.%m.%Y")
                else:
                    added_date = "N/A"
                
                if user_lang == "ru":
                    response += f"{i}. **{channel_name}** {status_emoji}\n"
                    response += f"   🌐 Языки перевода: {langs_text}\n"
                    response += f"   📅 Добавлен: {added_date}\n"
                    response += f"   📊 ID: `{channel['chat_id']}`\n\n"
                else:
                    response += f"{i}. **{channel_name}** {status_emoji}\n"
                    response += f"   🌐 Translation languages: {langs_text}\n"
                    response += f"   📅 Added: {added_date}\n"
                    response += f"   📊 ID: `{channel['chat_id']}`\n\n"
            
            if user_lang == "ru":
                response += "**📌 Обозначения:**\n✅ - Автоперевод включен\n⏸️ - Автоперевод выключен\n\n"
                response += "💡 **Совет:** Используйте команды в канале:\n"
                response += "• `/set_channel_langs en,ru` - изменить языки\n"
                response += "• `/toggle_autotranslate on/off` - вкл/выкл автоперевод"
            else:
                response += "**📌 Status Icons:**\n✅ - Auto-translation enabled\n⏸️ - Auto-translation disabled\n\n"
                response += "💡 **Tip:** Use commands in your channel:\n"
                response += "• `/set_channel_langs en,ru` - change languages\n"
                response += "• `/toggle_autotranslate on/off` - enable/disable auto-translation"
        
        await message.reply(response, parse_mode="Markdown")
        logger.info(f"Sent channels list to user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to get user channels: {e}")
        error_text = get_localized_string("translation_error", user_lang)
        try:
            await message.reply(error_text)
        except TelegramAPIError:
            pass


@router.message(Command("reset"))
async def reset_user_data(message: Message):
    """Handle /reset command to delete user data."""
    log_message_info(message, "reset command")
    
    user_id = message.from_user.id
    
    # Get user's language from database settings
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    try:
        await storage.delete_user_data(user_id)
        
        if user_lang == "ru":
            response = "✅ Ваши данные удалены."
        else:
            response = "✅ Your data has been deleted."
        
        await message.reply(response)
        logger.info(f"Reset user data for {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to reset user data: {e}")
        error_text = get_localized_string("translation_error", user_lang)
        try:
            await message.reply(error_text)
        except TelegramAPIError:
            pass


@router.message(Command("commands"))
async def commands_list(message: Message):
    """Handle /commands - show all available commands."""
    log_message_info(message, "commands list")
    
    user_id = message.from_user.id
    
    # Get user's language from database settings
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
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


@router.callback_query(F.data.in_(["setup_guide", "menu_setup_guide"]))
async def setup_guide_callback(callback: CallbackQuery):
    """Handle setup guide button."""
    user_id = callback.from_user.id
    
    # Get user's language from database settings
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    # Get bot username
    bot_username = (await callback.bot.get_me()).username
    
    # Get setup instructions
    instructions = get_localized_string("setup_instructions", user_lang, username=bot_username)
    
    back_text = "🔙 Назад в меню" if user_lang == "ru" else "🔙 Back to Menu"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data="back_to_menu")]
    ])
    
    try:
        await callback.message.edit_text(instructions, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        logger.info(f"Sent setup guide to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send setup guide: {e}")
        error_text = "❌ Ошибка отправки инструкции" if user_lang == "ru" else "❌ Error sending guide"
        await callback.answer(error_text)
