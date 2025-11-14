"""Comment handlers for translation in channel discussions."""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError

from ..core.logger import get_logger
from ..core.translate import translation_service, TranslationError
from ..core.database import storage, get_channel_target_languages
from ..core.i18n import (
    get_localized_string, 
    detect_user_language,
    extract_language_from_text,
    get_language_name
)
from ..core.utils import (
    extract_text_from_message,
    is_bot_mentioned,
    log_message_info,
    truncate_text_for_log
)

logger = get_logger(__name__)
router = Router()


@router.message(F.chat.type.in_(["group", "supergroup"]))
async def handle_group_message(message: Message):
    """Handle messages in groups/supergroups (comments)."""
    
    # Check if this is a reply to bot's message or bot is mentioned
    bot_username = (await message.bot.get_me()).username
    
    is_reply_to_bot = (
        message.reply_to_message and 
        message.reply_to_message.from_user and
        message.reply_to_message.from_user.id == message.bot.id
    )
    
    is_mentioned = is_bot_mentioned(message, bot_username)
    
    if not (is_reply_to_bot or is_mentioned):
        # Not relevant to bot
        return
    
    await _process_comment_translation(message)


async def _process_comment_translation(message: Message):
    """Process message for translation in comments."""
    log_message_info(message, "comment translation")
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    
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
    
    logger.info(f"Processing comment translation: {truncate_text_for_log(text)}")
    
    try:
        # Determine target language(s)
        target_langs = await _determine_target_languages(message, user_id, chat_id, text)
        
        if not target_langs:
            logger.debug("No target languages determined for comment")
            return
        
        # Detect source language
        source_lang = await translation_service.detect_language(text)
        
        # Filter out languages that match source
        target_langs = [lang for lang in target_langs if lang != source_lang]
        
        if not target_langs:
            user_lang = detect_user_language(text, user_id)
            same_lang_text = get_localized_string("same_language", user_lang)
            try:
                await message.reply(same_lang_text)
            except TelegramAPIError as e:
                logger.error(f"Failed to send same language message: {e}")
            return
        
        # Perform translations
        if len(target_langs) == 1:
            # Single translation
            result = await translation_service.translate(text, target_langs[0], source_lang)
            await _send_single_translation(message, result)
        else:
            # Multiple translations
            results = await translation_service.translate_multiple(text, target_langs, source_lang)
            await _send_multiple_translations(message, results, source_lang)
        
        logger.info(f"Comment translation completed: {source_lang}→{target_langs}")
        
    except TranslationError as e:
        logger.warning(f"Comment translation failed: {e}")
        user_lang = detect_user_language(text, user_id)
        error_text = get_localized_string("translation_error", user_lang)
        try:
            await message.reply(error_text)
        except TelegramAPIError:
            pass
    
    except Exception as e:
        logger.error(f"Unexpected error in comment translation: {e}")
        user_lang = detect_user_language(text, user_id)
        error_text = get_localized_string("translation_error", user_lang)
        try:
            await message.reply(error_text)
        except TelegramAPIError:
            pass


async def _determine_target_languages(message: Message, user_id: int, chat_id: int, text: str) -> list:
    """Determine target languages for translation."""
    
    # Check if user specified target language in text
    target_lang, clean_text = extract_language_from_text(text)
    
    if target_lang:
        return [target_lang]
    
    # Try to get user's preferred language
    try:
        user_settings = await storage.get_user_settings(user_id)
        user_target_lang = user_settings.get("target_lang") if user_settings else None
        
        if user_target_lang:
            return [user_target_lang]
    except Exception as e:
        logger.warning(f"Failed to get user settings: {e}")
    
    # Fallback to channel's target languages
    try:
        channel_langs = await get_channel_target_languages(chat_id)
        if channel_langs:
            return channel_langs
    except Exception as e:
        logger.warning(f"Failed to get channel languages: {e}")
    
    # Final fallback to English
    return ["en"]


async def _send_single_translation(message: Message, result):
    """Send a single translation result."""
    source_name = get_language_name(result.source_lang)
    target_name = get_language_name(result.target_lang)
    
    response = f"🌐 {source_name} → {target_name}:\n\n{result.text}"
    
    try:
        await message.reply(response)
    except TelegramAPIError as e:
        logger.error(f"Failed to send single translation: {e}")


async def _send_multiple_translations(message: Message, results: list, source_lang: str):
    """Send multiple translation results."""
    if not results:
        return
    
    # Format all translations into one message
    source_name = get_language_name(source_lang)
    response_parts = [f"🌐 **Translations from {source_name}:**\n"]
    
    for result in results:
        target_name = get_language_name(result.target_lang)
        response_parts.append(f"**→ {target_name}:**\n{result.text}\n")
    
    response = "\n".join(response_parts)
    
    # Check if message is too long
    from ..core.config import settings
    if len(response) > settings.max_comment_length:
        # Send translations separately
        for result in results:
            await _send_single_translation(message, result)
    else:
        try:
            await message.reply(response, parse_mode="Markdown")
        except TelegramAPIError as e:
            logger.error(f"Failed to send multiple translations: {e}")
            # Fallback to sending separately
            for result in results:
                await _send_single_translation(message, result)


# Handler for direct mentions in any chat type
@router.message(F.text.contains("@"))
async def handle_mention(message: Message):
    """Handle messages that mention the bot."""
    
    if message.chat.type == "private":
        # Private chats are handled elsewhere
        return
    
    bot_username = (await message.bot.get_me()).username
    
    if not is_bot_mentioned(message, bot_username):
        return
    
    # Process as comment translation
    await _process_comment_translation(message)


# Handler for replies to bot messages
@router.message(F.reply_to_message.from_user.id.func(lambda user_id, bot: user_id == bot.id))
async def handle_reply_to_bot(message: Message):
    """Handle replies to bot messages."""
    
    if message.chat.type == "private":
        # Private chats are handled elsewhere
        return
    
    # Process as comment translation
    await _process_comment_translation(message)

