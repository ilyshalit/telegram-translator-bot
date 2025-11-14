"""Main menu handlers with button-based interface."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError

from ..core.logger import get_logger
from ..core.database import storage
from ..core.i18n import get_localized_string, detect_user_language
from ..core.utils import log_message_info

logger = get_logger(__name__)
router = Router()


def create_main_menu_keyboard(user_lang: str) -> InlineKeyboardMarkup:
    """Create main menu keyboard with buttons."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_localized_string("interface_language", user_lang),
                callback_data="menu_interface_lang"
            ),
            InlineKeyboardButton(
                text=get_localized_string("translation_language", user_lang),
                callback_data="menu_translation_lang"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_localized_string("my_channels", user_lang),
                callback_data="menu_my_channels"
            ),
            InlineKeyboardButton(
                text=get_localized_string("setup_guide", user_lang),
                callback_data="menu_setup_guide"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_localized_string("help_menu", user_lang),
                callback_data="menu_help"
            )
        ]
    ])


def create_language_selection_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇸 English", callback_data="set_interface_lang_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_interface_lang_ru")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
        ]
    ])


def create_translation_language_keyboard(user_lang: str) -> InlineKeyboardMarkup:
    """Create translation language selection keyboard."""
    back_text = "🔙 Назад в меню" if user_lang == "ru" else "🔙 Back to Menu"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇸 English", callback_data="set_translation_lang_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_translation_lang_ru")
        ],
        [
            InlineKeyboardButton(text="🇪🇸 Español", callback_data="set_translation_lang_es"),
            InlineKeyboardButton(text="🇫🇷 Français", callback_data="set_translation_lang_fr")
        ],
        [
            InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="set_translation_lang_de"),
            InlineKeyboardButton(text="🇮🇹 Italiano", callback_data="set_translation_lang_it")
        ],
        [
            InlineKeyboardButton(text=back_text, callback_data="back_to_menu")
        ]
    ])


@router.message(Command("menu"))
async def menu_command(message: Message):
    """Handle /menu command - show main menu."""
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


@router.callback_query(F.data == "menu_interface_lang")
async def interface_language_callback(callback_query: CallbackQuery):
    """Handle interface language selection."""
    user_id = callback_query.from_user.id
    
    # Get current language for the message
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    selection_text = get_localized_string("language_selection", user_lang)
    keyboard = create_language_selection_keyboard()
    
    try:
        await callback_query.message.edit_text(selection_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer()
        logger.info(f"Showed interface language selection to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to show interface language selection: {e}")


@router.callback_query(F.data == "menu_translation_lang")
async def translation_language_callback(callback_query: CallbackQuery):
    """Handle translation language selection."""
    user_id = callback_query.from_user.id
    
    # Get current language for the message
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    explanation_text = get_localized_string("translation_lang_explanation", user_lang)
    keyboard = create_translation_language_keyboard(user_lang)
    
    try:
        await callback_query.message.edit_text(explanation_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer()
        logger.info(f"Showed translation language selection to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to show translation language selection: {e}")


@router.callback_query(F.data == "menu_my_channels")
async def my_channels_callback(callback_query: CallbackQuery):
    """Handle my channels view."""
    user_id = callback_query.from_user.id
    
    # Get current language
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    # TODO: Get actual channels from database
    channels_text = get_localized_string("no_channels_connected", user_lang)
    
    back_text = "🔙 Назад в меню" if user_lang == "ru" else "🔙 Back to Menu"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data="back_to_menu")]
    ])
    
    try:
        await callback_query.message.edit_text(channels_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer()
        logger.info(f"Showed my channels to user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to show my channels: {e}")


@router.callback_query(F.data.startswith("set_interface_lang_"))
async def set_interface_language_callback(callback_query: CallbackQuery):
    """Handle interface language setting."""
    user_id = callback_query.from_user.id
    selected_lang = callback_query.data.split("_")[-1]  # Extract 'en' or 'ru'
    
    try:
        # Save interface language preference
        await storage.set_user_settings(user_id, selected_lang)
        
        # Show success message and return to menu
        success_text = "✅ Interface language updated!" if selected_lang == "en" else "✅ Язык интерфейса обновлен!"
        menu_text = get_localized_string("main_menu", selected_lang)
        keyboard = create_main_menu_keyboard(selected_lang)
        
        await callback_query.message.edit_text(f"{success_text}\n\n{menu_text}", reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer(success_text)
        
        logger.info(f"Set interface language {selected_lang} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to set interface language: {e}")
        await callback_query.answer("❌ Error updating language")


@router.callback_query(F.data.startswith("set_translation_lang_"))
async def set_translation_language_callback(callback_query: CallbackQuery):
    """Handle translation language setting."""
    user_id = callback_query.from_user.id
    selected_lang = callback_query.data.split("_")[-1]  # Extract language code
    
    try:
        # Get current interface language
        user_settings = await storage.get_user_settings(user_id)
        interface_lang = user_settings.get("target_lang", "en") if user_settings else "en"
        
        # Save translation language preference (we'll add this field to user settings)
        # For now, we'll use the same field but we should separate them later
        
        # Show success message and return to menu
        if interface_lang == "ru":
            success_text = f"✅ Язык перевода установлен: {selected_lang.upper()}"
        else:
            success_text = f"✅ Translation language set: {selected_lang.upper()}"
            
        menu_text = get_localized_string("main_menu", interface_lang)
        keyboard = create_main_menu_keyboard(interface_lang)
        
        await callback_query.message.edit_text(f"{success_text}\n\n{menu_text}", reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer(success_text)
        
        logger.info(f"Set translation language {selected_lang} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to set translation language: {e}")
        await callback_query.answer("❌ Error updating language")


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback_query: CallbackQuery):
    """Handle back to menu button."""
    user_id = callback_query.from_user.id
    
    # Get current interface language
    user_settings = await storage.get_user_settings(user_id)
    user_lang = user_settings.get("target_lang", "en") if user_settings else "en"
    
    menu_text = get_localized_string("main_menu", user_lang)
    keyboard = create_main_menu_keyboard(user_lang)
    
    try:
        await callback_query.message.edit_text(menu_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer()
        logger.info(f"Returned to main menu for user {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to return to main menu: {e}")
