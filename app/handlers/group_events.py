"""Handlers for group events like bot being added to channel."""

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, ADMINISTRATOR, MEMBER, KICKED, LEFT
from aiogram.exceptions import TelegramAPIError

from ..core.logger import get_logger
from ..core.database import storage
from ..core.i18n import get_localized_string, detect_user_language
from ..core.utils import log_message_info

logger = get_logger(__name__)
router = Router()


async def check_channel_discussion_group(bot, chat_id: int) -> bool:
    """Check if channel has discussion group enabled."""
    try:
        # Try to get chat info
        chat = await bot.get_chat(chat_id)
        
        # For channels, check if linked_chat_id exists (discussion group)
        if chat.type == "channel":
            return chat.linked_chat_id is not None
        
        # For supergroups, they can have comments by default
        return True
        
    except Exception as e:
        logger.error(f"Failed to check discussion group for {chat_id}: {e}")
        return False


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR))
async def bot_added_as_admin(event: ChatMemberUpdated):
    """Handle bot being added as administrator to a channel/group."""
    chat = event.chat
    user = event.from_user
    
    # Only handle channels and supergroups
    if chat.type not in ["channel", "supergroup"]:
        return
        
    logger.info(f"Bot added as admin to {chat.type} {chat.id} by user {user.id}")
    
    # Save user-channel relationship
    await storage.add_user_channel(user.id, chat.id, chat.title)
    
    # Get user's language preference
    user_settings = await storage.get_user_settings(user.id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    # Check if channel has discussion group
    has_discussion = await check_channel_discussion_group(event.bot, chat.id)
    
    if not has_discussion and chat.type == "channel":
        # Channel needs discussion group
        no_discussion_text = get_localized_string("channel_no_discussion", user_lang)
        check_again_text = get_localized_string("check_discussion_again", user_lang)
        how_enable_text = get_localized_string("how_enable_discussion", user_lang)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=check_again_text, callback_data=f"check_discussion_{chat.id}"),
                InlineKeyboardButton(text=how_enable_text, callback_data="show_discussion_help")
            ]
        ])
        
        try:
            await event.bot.send_message(
                chat_id=user.id,
                text=no_discussion_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            logger.info(f"Sent discussion group requirement to user {user.id}")
        except Exception as e:
            logger.error(f"Failed to send discussion requirement: {e}")
        return
    
    # Channel is ready, show language setup
    welcome_text = get_localized_string("channel_welcome", user_lang)
    
    # Create language selection keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇸 English", callback_data=f"channel_lang_{chat.id}_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"channel_lang_{chat.id}_ru")
        ],
        [
            InlineKeyboardButton(text="🇪🇸 Español", callback_data=f"channel_lang_{chat.id}_es"),
            InlineKeyboardButton(text="🇫🇷 Français", callback_data=f"channel_lang_{chat.id}_fr")
        ],
        [
            InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data=f"channel_lang_{chat.id}_de"),
            InlineKeyboardButton(text="🇮🇹 Italiano", callback_data=f"channel_lang_{chat.id}_it")
        ],
        [
            InlineKeyboardButton(text="✅ Done", callback_data=f"channel_setup_done_{chat.id}")
        ]
    ])
    
    try:
        # ВАЖНО: Отправляем сообщение только в ЛС пользователю, НЕ в канал!
        await event.bot.send_message(
            chat_id=user.id,
            text=welcome_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        logger.info(f"Sent channel setup message to user {user.id} (private message)")
    except Exception as e:
        logger.error(f"Failed to send channel setup message to user {user.id}: {e}")


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED | LEFT))
async def bot_removed_from_chat(event: ChatMemberUpdated):
    """Handle bot being removed from a channel/group."""
    chat = event.chat
    user = event.from_user
    
    # Only handle channels and supergroups
    if chat.type not in ["channel", "supergroup"]:
        return
        
    logger.info(f"Bot removed from {chat.type} {chat.id} by user {user.id}")
    
    # Remove user-channel relationship
    await storage.remove_user_channel(user.id, chat.id)


@router.callback_query(F.data.startswith("check_discussion_"))
async def check_discussion_callback(callback_query):
    """Handle re-checking discussion group."""
    chat_id = int(callback_query.data.split("_")[-1])
    
    try:
        # Get user language
        user_settings = await storage.get_user_settings(callback_query.from_user.id)
        user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
        
        # Check if discussion group is now enabled
        has_discussion = await check_channel_discussion_group(callback_query.bot, chat_id)
        
        if has_discussion:
            # Success! Show language setup
            welcome_text = get_localized_string("channel_welcome", user_lang)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🇺🇸 English", callback_data=f"channel_lang_{chat_id}_en"),
                    InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"channel_lang_{chat_id}_ru")
                ],
                [
                    InlineKeyboardButton(text="🇪🇸 Español", callback_data=f"channel_lang_{chat_id}_es"),
                    InlineKeyboardButton(text="🇫🇷 Français", callback_data=f"channel_lang_{chat_id}_fr")
                ],
                [
                    InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data=f"channel_lang_{chat_id}_de"),
                    InlineKeyboardButton(text="🇮🇹 Italiano", callback_data=f"channel_lang_{chat_id}_it")
                ],
                [
                    InlineKeyboardButton(text="✅ Done", callback_data=f"channel_setup_done_{chat_id}")
                ]
            ])
            
            await callback_query.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback_query.answer("✅ Discussion group found!")
        else:
            # Still no discussion group
            await callback_query.answer("❌ Discussion group still not found. Please enable it first.")
            
    except Exception as e:
        logger.error(f"Failed to check discussion group: {e}")
        await callback_query.answer("❌ Error checking discussion group")


@router.callback_query(F.data == "show_discussion_help")
async def show_discussion_help_callback(callback_query):
    """Show how to enable discussion group."""
    try:
        # Get user language
        user_settings = await storage.get_user_settings(callback_query.from_user.id)
        user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
        
        instructions_text = get_localized_string("discussion_instructions", user_lang)
        back_text = "🔙 Back" if user_lang == "en" else "🔙 Назад"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=back_text, callback_data="back_to_discussion_check")]
        ])
        
        await callback_query.message.edit_text(instructions_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Failed to show discussion help: {e}")


@router.callback_query(F.data == "back_to_discussion_check")
async def back_to_discussion_check_callback(callback_query):
    """Go back to discussion check screen."""
    try:
        # Get user language
        user_settings = await storage.get_user_settings(callback_query.from_user.id)
        user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
        
        no_discussion_text = get_localized_string("channel_no_discussion", user_lang)
        check_again_text = get_localized_string("check_discussion_again", user_lang)
        how_enable_text = get_localized_string("how_enable_discussion", user_lang)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=check_again_text, callback_data="check_discussion_unknown"),
                InlineKeyboardButton(text=how_enable_text, callback_data="show_discussion_help")
            ]
        ])
        
        await callback_query.message.edit_text(no_discussion_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Failed to go back to discussion check: {e}")


@router.callback_query(F.data.startswith("channel_lang_"))
async def channel_language_callback(callback_query):
    """Handle channel language selection."""
    data_parts = callback_query.data.split("_")
    chat_id = int(data_parts[2])
    selected_lang = data_parts[3]
    
    try:
        # Get current channel settings or create new
        channel_settings = await storage.get_channel_settings(chat_id)
        
        # Update target languages (add to existing or create new list)
        current_langs = channel_settings.get("target_langs", []) if channel_settings else []
        if selected_lang not in current_langs:
            current_langs.append(selected_lang)
            
        # Save updated settings - используем правильный формат для storage
        await storage.set_channel_settings(chat_id, target_langs=current_langs, autotranslate=True)
        
        # Update the message to show selected languages
        user_lang = "en"  # Default for now
        user_settings = await storage.get_user_settings(callback_query.from_user.id)
        if user_settings:
            user_lang = user_settings.get("target_lang", "en")
            
        selected_text = f"✅ Selected: {', '.join(current_langs).upper()}"
        welcome_text = get_localized_string("channel_welcome", user_lang)
        
        updated_text = f"{welcome_text}\n\n{selected_text}"
        
        await callback_query.message.edit_text(updated_text, reply_markup=callback_query.message.reply_markup, parse_mode="Markdown")
        await callback_query.answer(f"Added {selected_lang.upper()}")
        
        logger.info(f"Added language {selected_lang} to channel {chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to set channel language: {e}")
        await callback_query.answer("❌ Error setting language")


@router.callback_query(F.data.startswith("channel_setup_done_"))
async def channel_setup_done_callback(callback_query):
    """Handle channel setup completion."""
    chat_id = int(callback_query.data.split("_")[-1])
    
    try:
        # Get user language
        user_settings = await storage.get_user_settings(callback_query.from_user.id)
        user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
        
        success_text = get_localized_string("channel_setup_success", user_lang)
        
        await callback_query.message.edit_text(success_text, parse_mode="Markdown")
        await callback_query.answer("✅ Setup complete!")
        
        logger.info(f"Channel setup completed for {chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to complete channel setup: {e}")
        await callback_query.answer("❌ Error completing setup")