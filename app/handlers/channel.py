"""Channel handlers for auto-translation of posts."""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

from ..core.logger import get_logger
from ..core.translate import translation_service, TranslationError
from ..core.database import storage, is_autotranslate_enabled, get_channel_target_languages
from ..core.i18n import (
    get_localized_string, 
    detect_user_language,
    parse_language_list,
    get_language_name
)
from ..core.utils import (
    extract_text_from_message,
    extract_command_args,
    validate_language_list,
    split_long_message,
    log_message_info,
    truncate_text_for_log
)
from ..core.config import settings

logger = get_logger(__name__)
router = Router()


@router.message(Command("set_channel_langs"))
async def set_channel_languages(message: Message, is_admin: bool = False):
    """Handle /set_channel_langs command (admin only)."""
    log_message_info(message, "set channel languages")
    
    if not is_admin:
        # This should be handled by middleware, but double-check
        return
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_lang = detect_user_language(message.text or "", user_id)
    
    # Extract language list from command
    langs_arg = extract_command_args(message.text, "set_channel_langs")
    
    if not langs_arg:
        error_text = "Usage: /set_channel_langs en,ru,tr"
        try:
            # Send to private chat, not to channel
            await message.bot.send_message(chat_id=user_id, text=error_text)
        except TelegramAPIError as e:
            logger.error(f"Failed to send usage message: {e}")
        return
    
    # Validate language list
    is_valid, languages, error_msg = validate_language_list(langs_arg)
    
    if not is_valid:
        error_text = f"❌ {error_msg}"
        try:
            # Send to private chat, not to channel
            await message.bot.send_message(chat_id=user_id, text=error_text)
        except TelegramAPIError as e:
            logger.error(f"Failed to send validation error: {e}")
        return
    
    try:
        # Save channel settings
        await storage.set_channel_settings(chat_id, target_langs=languages)
        
        # Format language names for response
        lang_names = [get_language_name(lang, user_lang) for lang in languages]
        langs_display = ", ".join(lang_names)
        
        success_text = get_localized_string(
            "channel_langs_set",
            user_lang,
            languages=langs_display
        )
        
        # Send to private chat, not to channel
        await message.bot.send_message(chat_id=user_id, text=success_text)
        logger.info(f"Set channel languages {languages} for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to set channel languages: {e}")
        error_text = get_localized_string("translation_error", user_lang)
        try:
            # Send to private chat, not to channel
            await message.bot.send_message(chat_id=user_id, text=error_text)
        except TelegramAPIError:
            pass


@router.message(Command("toggle_autotranslate"))
async def toggle_autotranslate(message: Message, is_admin: bool = False):
    """Handle /toggle_autotranslate command (admin only)."""
    log_message_info(message, "toggle autotranslate")
    
    if not is_admin:
        return
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_lang = detect_user_language(message.text or "", user_id)
    
    # Extract on/off argument
    toggle_arg = extract_command_args(message.text, "toggle_autotranslate")
    
    if not toggle_arg or toggle_arg.lower() not in ["on", "off"]:
        error_text = "Usage: /toggle_autotranslate on|off"
        try:
            # Send to private chat, not to channel
            await message.bot.send_message(chat_id=user_id, text=error_text)
        except TelegramAPIError as e:
            logger.error(f"Failed to send toggle usage: {e}")
        return
    
    enable = toggle_arg.lower() == "on"
    
    try:
        # Update channel settings
        await storage.set_channel_settings(chat_id, autotranslate=enable)
        
        if enable:
            success_text = get_localized_string("autotranslate_enabled", user_lang)
        else:
            success_text = get_localized_string("autotranslate_disabled", user_lang)
        
        # Send to private chat, not to channel
        await message.bot.send_message(chat_id=user_id, text=success_text)
        logger.info(f"Set autotranslate {enable} for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to toggle autotranslate: {e}")
        error_text = get_localized_string("translation_error", user_lang)
        try:
            # Send to private chat, not to channel
            await message.bot.send_message(chat_id=user_id, text=error_text)
        except TelegramAPIError:
            pass


@router.message(Command("stats"))
async def channel_stats(message: Message, is_admin: bool = False):
    """Handle /stats command (admin only)."""
    log_message_info(message, "channel stats")
    
    if not is_admin:
        return
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_lang = detect_user_language(message.text or "", user_id)
    
    try:
        # Get statistics
        stats_24h = await storage.get_translation_stats(chat_id, days=1)
        stats_7d = await storage.get_translation_stats(chat_id, days=7)
        
        stats_text = get_localized_string(
            "stats_message",
            user_lang,
            posts_24h=stats_24h["posts"],
            translations_24h=stats_24h["translations"],
            posts_7d=stats_7d["posts"],
            translations_7d=stats_7d["translations"]
        )
        
        # Send to private chat, not to channel
        await message.bot.send_message(chat_id=user_id, text=stats_text, parse_mode="Markdown")
        logger.info(f"Sent stats to user {user_id} for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to get channel stats: {e}")
        error_text = get_localized_string("translation_error", user_lang)
        try:
            # Send to private chat, not to channel
            await message.bot.send_message(chat_id=user_id, text=error_text)
        except TelegramAPIError:
            pass


@router.channel_post()
async def handle_channel_post(message: Message):
    """Handle new channel posts for auto-translation."""
    logger.info(f"Received channel post in chat {message.chat.id}: {message.message_id}")
    await _process_channel_post(message, is_edited=False)


@router.edited_channel_post()
async def handle_edited_channel_post(message: Message):
    """Handle edited channel posts for auto-translation."""
    logger.info(f"Received edited channel post in chat {message.chat.id}: {message.message_id}")
    await _process_channel_post(message, is_edited=True)


@router.message(F.chat.type.in_(["channel", "supergroup"]))
async def handle_channel_and_group_messages(message: Message):
    """Handle messages in channels and supergroups (including discussion groups)."""
    logger.info(f"DEBUG: Received message in {message.chat.type} {message.chat.id}: {message.message_id}, from_user: {message.from_user}")
    
    # Check if this is a forwarded channel post or automatic channel message
    if (message.chat.type == "supergroup" and 
        message.from_user and 
        message.from_user.id == 777000):  # Telegram service messages
        
        logger.info(f"Processing forwarded channel post in discussion group {message.chat.id}")
        await _process_channel_post(message, is_edited=False)
        return
    
    # Check if this is a regular channel post
    if message.chat.type == "channel":
        logger.info(f"Processing direct channel post in {message.chat.id}")
        await _process_channel_post(message, is_edited=False)
        return
    
    # For other supergroup messages, let the comments handler deal with them
    logger.debug(f"Skipping message processing for {message.chat.type} {message.chat.id}")


async def _process_channel_post(message: Message, is_edited: bool = False):
    """Process channel post for auto-translation."""
    chat_id = message.chat.id
    
    log_message_info(message, f"channel post {'(edited)' if is_edited else ''}")
    
    try:
        # Check if auto-translation is enabled
        if not await is_autotranslate_enabled(chat_id):
            logger.debug(f"Auto-translation disabled for chat {chat_id}")
            return
        
        # Extract text from post
        text = extract_text_from_message(message)
        
        if not text:
            logger.debug(f"No text found in channel post {message.message_id}")
            return
        
        logger.info(f"Processing channel post: {truncate_text_for_log(text)}")
        
        # Get target languages for this channel
        target_languages = await get_channel_target_languages(chat_id)
        
        if not target_languages:
            logger.warning(f"No target languages configured for chat {chat_id}")
            return
        
        # Detect source language
        source_lang = await translation_service.detect_language(text)
        
        # Filter out languages that match source
        target_languages = [
            lang for lang in target_languages 
            if lang != source_lang
        ]
        
        if not target_languages:
            logger.debug(f"No translation needed - source language {source_lang} matches targets")
            return
        
        # Perform translations
        translations = await translation_service.translate_multiple(
            text, target_languages, source_lang
        )
        
        if not translations:
            logger.warning(f"No translations produced for post {message.message_id}")
            return
        
        # Format translation comments
        comment_messages = _format_translation_comments(
            translations, source_lang, is_edited
        )
        
        # Post comments
        await _post_translation_comments(message, comment_messages)
        
        # Record statistics
        await storage.record_translation_stats(
            chat_id, 
            posts=1, 
            translations=len(translations)
        )
        
        logger.info(
            f"Posted {len(comment_messages)} translation comments for post {message.message_id}"
        )
        
    except TranslationError as e:
        logger.warning(f"Translation failed for channel post: {e}")
    
    except Exception as e:
        logger.error(f"Unexpected error processing channel post: {e}")


def _format_translation_comments(translations, source_lang: str, is_edited: bool = False) -> list:
    """Format translations into comment messages."""
    if not translations:
        return []
    
    messages = []
    current_message = ""
    
    for translation in translations:
        translated_text = translation.text
        
        # Create simple translation block - just the translated text
        block = f"{translated_text}\n\n"
        
        # Check if we can add this block to current message
        if len(current_message) + len(block) <= settings.max_comment_length:
            current_message += block
        else:
            # Save current message and start new one
            if current_message:
                messages.append(current_message.strip())
            current_message = block
    
    # Add remaining message
    if current_message:
        messages.append(current_message.strip())
    
    return messages


async def _post_translation_comments(original_message: Message, comment_messages: list):
    """Post translation comments to the channel."""
    if not comment_messages:
        return
    
    chat_id = original_message.chat.id
    message_id = original_message.message_id
    
    for comment_text in comment_messages:
        try:
            # Post comment as reply to original message
            await original_message.bot.send_message(
                chat_id=chat_id,
                text=comment_text,
                reply_to_message_id=message_id,
                allow_sending_without_reply=True,
                parse_mode="Markdown"
            )
            
            # Small delay between comments to avoid rate limits
            import asyncio
            await asyncio.sleep(0.5)
            
        except TelegramBadRequest as e:
            if "replied message not found" in str(e).lower():
                logger.warning(f"Original message not found for reply in chat {chat_id}")
            elif "comments are disabled" in str(e).lower():
                logger.warning(f"Comments disabled in chat {chat_id}")
                await _notify_admin_about_comments(original_message)
            elif "not enough rights" in str(e).lower():
                logger.warning(f"Bot lacks permissions to post in chat {chat_id}")
                await _notify_admin_about_permissions(original_message)
            else:
                logger.error(f"Failed to post comment: {e}")
        
        except TelegramAPIError as e:
            logger.error(f"API error posting comment: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error posting comment: {e}")


async def _notify_admin_about_comments(message: Message):
    """Notify channel admin about disabled comments (once)."""
    chat_id = message.chat.id
    
    # Use a simple flag to avoid spam (you might want to use Redis or database for this)
    cache_key = f"comments_notified_{chat_id}"
    
    # For now, just log the issue
    logger.warning(f"Comments are disabled for channel {chat_id}")
    
    # TODO: Implement admin notification via private message
    # This would require storing admin user IDs when they add the bot


async def _notify_admin_about_permissions(message: Message):
    """Notify about insufficient bot permissions."""
    chat_id = message.chat.id
    
    logger.warning(f"Bot lacks admin permissions in chat {chat_id}")
    
    # TODO: Implement admin notification
    # This would require storing admin user IDs when they add the bot

