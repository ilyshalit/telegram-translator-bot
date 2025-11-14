"""Internationalization and language detection utilities."""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class SupportedLanguage(str, Enum):
    """Supported language codes (ISO 639-1)."""
    
    ENGLISH = "en"
    RUSSIAN = "ru"
    TURKISH = "tr"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"
    HINDI = "hi"
    DUTCH = "nl"
    POLISH = "pl"
    UKRAINIAN = "uk"


# Language name mappings
LANGUAGE_NAMES = {
    "en": {"en": "English", "ru": "Английский"},
    "ru": {"en": "Russian", "ru": "Русский"},
    "tr": {"en": "Turkish", "ru": "Турецкий"},
    "es": {"en": "Spanish", "ru": "Испанский"},
    "fr": {"en": "French", "ru": "Французский"},
    "de": {"en": "German", "ru": "Немецкий"},
    "it": {"en": "Italian", "ru": "Итальянский"},
    "pt": {"en": "Portuguese", "ru": "Португальский"},
    "zh": {"en": "Chinese", "ru": "Китайский"},
    "ja": {"en": "Japanese", "ru": "Японский"},
    "ko": {"en": "Korean", "ru": "Корейский"},
    "ar": {"en": "Arabic", "ru": "Арабский"},
    "hi": {"en": "Hindi", "ru": "Хинди"},
    "nl": {"en": "Dutch", "ru": "Голландский"},
    "pl": {"en": "Polish", "ru": "Польский"},
    "uk": {"en": "Ukrainian", "ru": "Украинский"},
}

# Localized strings
STRINGS = {
    "en": {
        "start_message": "🐟 Hello!\nThis bot will translate messages in your group. It supports 134 languages and has various modes.\n\n📺 **For CHANNELS**: Add bot to your channel as admin\n➕ **For GROUPS**: Add bot to your group chat\n\n🤖 **How it works:**\n• Bot communicates only in private messages\n• Translates channel posts in comments automatically\n• Translates group messages when mentioned\n\n🔒 **SAFE PERMISSIONS**: Enable only:\n✅ Administrator rights (basic)\n❌ Turn OFF all other permissions!",
        "main_menu": "🏠 **Main Menu**\n\nChoose an option:",
        "interface_language": "🌐 Interface Language",
        "translation_language": "🔄 Translation Language", 
        "my_channels": "📺 My Channels",
        "setup_guide": "📋 Setup Guide",
        "help_menu": "❓ Help",
        "language_selection": "🌐 **Choose Interface Language**\n\nSelect your preferred language for bot messages:",
        "translation_lang_explanation": "🔄 **Translation Language Settings**\n\nThis setting determines which language the bot will translate posts and messages TO in your channels.\n\nExample: If you set Russian, all posts will be translated to Russian in comments.",
        "no_channels_connected": "📺 **My Channels**\n\n❌ No channels connected yet.\n\nTo connect a channel:\n1. Add bot to your channel as admin\n2. Follow setup instructions\n3. Your channels will appear here",
        "channel_setup_success": "✅ **Channel Setup Complete!**\n\nYour channel is now connected and ready to translate posts automatically!\n\n🎯 **What happens next:**\n• Post anything in your channel\n• Bot will automatically add translations in comments\n• Users can also request translations by mentioning the bot",
        "channel_no_discussion": "⚠️ **Discussion Group Required**\n\nYour channel needs a discussion group for the bot to add translation comments.\n\n📋 **How to enable:**\n1. Go to your channel settings\n2. Tap 'Discussion'\n3. Create or link a group\n4. Come back and try again",
        "check_discussion_again": "🔄 Check Again",
        "how_enable_discussion": "📋 How to Enable Discussion",
        "discussion_instructions": "📋 **How to Enable Channel Discussion**\n\n**Step 1:** Open your channel\n**Step 2:** Tap the channel name at the top\n**Step 3:** Tap 'Edit'\n**Step 4:** Scroll down and tap 'Discussion'\n**Step 5:** Choose 'Create Group' or link existing group\n**Step 6:** Tap 'Create' or 'Link'\n\n✅ Done! Now posts will have comment sections.",
        "channel_welcome": "🎉 **Bot Successfully Added!**\n\nNow let's set up automatic translation for your channel posts.\n\n**Select translation languages:**\nChoose which languages you want posts to be translated to in comments.",
        "help_message": """🌐 **Translation Bot Help**

**In Private Chat:**
• Send any text - get translation
• /set_my_lang <code> - set your preferred language
• /privacy - privacy policy
• /provider - current translation provider

**In Channel Comments:**
• Reply to my comment or mention me @{username}
• I'll translate your message

**Admin Commands (in channels):**
• /set_channel_langs <list> - set target languages (e.g., en,ru,tr)
• /toggle_autotranslate on|off - enable/disable auto-translation
• /stats - translation statistics

**Supported Languages:**
{languages}

**Examples:**
• "Hello world" → "Привет мир" (if target is Russian)
• "переведи на en: Привет" → "Hello"
""",
        "language_set": "✅ Your language has been set to: {language}",
        "invalid_language": "❌ Invalid language code. Supported: {languages}",
        "channel_langs_set": "✅ Channel target languages set to: {languages}",
        "autotranslate_enabled": "✅ Auto-translation enabled for this channel",
        "autotranslate_disabled": "❌ Auto-translation disabled for this channel",
        "admin_only": "⚠️ This command is only available to channel administrators",
        "rate_limit": "⏰ Please wait a moment before sending another request",
        "translation_error": "❌ Translation failed. Please try again later",
        "no_text": "❌ No text to translate",
        "same_language": "ℹ️ Text is already in the target language",
        "privacy_message": """🔒 **Privacy Policy**

**What we log:**
• Translation requests (without personal data)
• Error messages and system events
• Usage statistics (anonymized)

**What we DON'T log:**
• Your personal messages content
• User IDs or usernames
• API keys or tokens

**Data storage:**
• Language preferences (can be deleted with /reset)
• Channel settings (admin-controlled)

**To delete your data:**
Contact the bot administrator.
""",
        "provider_info": "🔧 Current translation provider: {provider}",
        "stats_message": """📊 **Translation Statistics**

**Last 24 hours:**
• Posts translated: {posts_24h}
• Total translations: {translations_24h}

**Last 7 days:**
• Posts translated: {posts_7d}
• Total translations: {translations_7d}
""",
        "comments_disabled": "⚠️ Comments are disabled for this channel. Enable discussions to use auto-translation.",
        "bot_not_admin": "⚠️ I need to be an administrator in this channel to post comments.",
        "translation_header": "🌐 Translation ({source}→{target}):",
        "translation_edited": "🌐 Translation ({source}→{target}) (edited):",
        "add_to_group": "➕ Add to Group",
        "add_to_channel": "📺 Add to Channel",
        "setup_instructions": """📋 **Setup Instructions**

**Step 1: Add bot to your channel**
1. Go to your channel settings
2. Click "Administrators" 
3. Click "Add Administrator"
4. Search for @{username}
5. Add the bot

**Step 2: Set bot permissions (SAFE)**
✅ **Enable only:**
• Administrator rights (basic level)

❌ **DISABLE all other permissions:**
• Change description
• Delete messages
• Ban users
• Invite links
• Pin messages
• Manage video chats
• Anonymous mode

**Step 3: Enable Discussions**
1. Go to channel settings
2. Enable "Discussion Group"
3. This allows comments on posts

**Step 4: Configure languages**
Send this command in your channel:
`/set_channel_langs en,ru`

**Step 5: Test it!**
Post any message in your channel - bot will automatically add translation in comments!

🔒 **Security**: Bot only needs minimal permissions to work safely.""",
        "supported_languages": "🌐 **Supported Languages**: English, Russian, Turkish, Spanish, French, German, Italian, Portuguese, Chinese, Japanese, Korean, Arabic, Hindi, Dutch, Polish, Ukrainian and 120+ more languages!\n\n🛡️ **Security Note**: This bot is designed with privacy and security in mind. It only requires minimal permissions and never stores your messages.",
    },
    "ru": {
        "start_message": "🐟 Привет!\nЭтот бот будет переводить сообщения в вашей группе. Он поддерживает 134 языка и имеет различные режимы.\n\n📺 **Для КАНАЛОВ**: Добавьте бота в канал как администратора\n➕ **Для ГРУПП**: Добавьте бота в групповой чат\n\n🤖 **Как работает:**\n• Бот общается только в личных сообщениях\n• Переводит посты канала в комментариях автоматически\n• Переводит сообщения группы при упоминании\n\n🔒 **БЕЗОПАСНЫЕ ПРАВА**: Включите только:\n✅ Права администратора (базовые)\n❌ Все остальные права ВЫКЛЮЧИТЕ!",
        "main_menu": "🏠 **Главное меню**\n\nВыберите опцию:",
        "interface_language": "🌐 Язык интерфейса",
        "translation_language": "🔄 Язык перевода",
        "my_channels": "📺 Мои каналы", 
        "setup_guide": "📋 Инструкция",
        "help_menu": "❓ Помощь",
        "language_selection": "🌐 **Выбор языка интерфейса**\n\nВыберите предпочитаемый язык для сообщений бота:",
        "translation_lang_explanation": "🔄 **Настройки языка перевода**\n\nЭта настройка определяет, НА КАКОЙ язык бот будет переводить посты и сообщения в ваших каналах.\n\nПример: Если выберете русский, все посты будут переводиться на русский в комментариях.",
        "no_channels_connected": "📺 **Мои каналы**\n\n❌ Каналы пока не подключены.\n\nЧтобы подключить канал:\n1. Добавьте бота в канал как администратора\n2. Следуйте инструкции настройки\n3. Ваши каналы появятся здесь",
        "channel_setup_success": "✅ **Настройка канала завершена!**\n\nВаш канал подключен и готов автоматически переводить посты!\n\n🎯 **Что происходит дальше:**\n• Опубликуйте любой пост в канале\n• Бот автоматически добавит переводы в комментариях\n• Пользователи также могут запросить перевод, упомянув бота",
        "channel_no_discussion": "⚠️ **Нужна группа обсуждений**\n\nВашему каналу нужна группа обсуждений, чтобы бот мог добавлять переводы в комментариях.\n\n📋 **Как включить:**\n1. Зайдите в настройки канала\n2. Нажмите 'Обсуждение'\n3. Создайте или привяжите группу\n4. Вернитесь и попробуйте снова",
        "check_discussion_again": "🔄 Проверить снова",
        "how_enable_discussion": "📋 Как включить обсуждения",
        "discussion_instructions": "📋 **Как включить обсуждения канала**\n\n**Шаг 1:** Откройте ваш канал\n**Шаг 2:** Нажмите на название канала вверху\n**Шаг 3:** Нажмите 'Изменить'\n**Шаг 4:** Прокрутите вниз и нажмите 'Обсуждение'\n**Шаг 5:** Выберите 'Создать группу' или привяжите существующую\n**Шаг 6:** Нажмите 'Создать' или 'Привязать'\n\n✅ Готово! Теперь у постов будут комментарии.",
        "channel_welcome": "🎉 **Бот успешно добавлен!**\n\nТеперь настроим автоматический перевод постов вашего канала.\n\n**Выберите языки перевода:**\nВыберите на какие языки переводить посты в комментариях.",
        "help_message": """🌐 **Помощь по боту-переводчику**

**В личных сообщениях:**
• Отправь любой текст - получи перевод
• /set_my_lang <код> - установить предпочитаемый язык
• /privacy - политика конфиденциальности
• /provider - текущий провайдер переводов

**В комментариях канала:**
• Ответь на мой комментарий или упомяни меня @{username}
• Я переведу твое сообщение

**Команды администратора (в каналах):**
• /set_channel_langs <список> - установить целевые языки (например, en,ru,tr)
• /toggle_autotranslate on|off - включить/выключить автоперевод
• /stats - статистика переводов

**Поддерживаемые языки:**
{languages}

**Примеры:**
• "Hello world" → "Привет мир" (если цель - русский)
• "переведи на en: Привет" → "Hello"
""",
        "language_set": "✅ Ваш язык установлен на: {language}",
        "invalid_language": "❌ Неверный код языка. Поддерживаются: {languages}",
        "channel_langs_set": "✅ Целевые языки канала установлены на: {languages}",
        "autotranslate_enabled": "✅ Автоперевод включен для этого канала",
        "autotranslate_disabled": "❌ Автоперевод выключен для этого канала",
        "admin_only": "⚠️ Эта команда доступна только администраторам канала",
        "rate_limit": "⏰ Пожалуйста, подождите немного перед отправкой следующего запроса",
        "translation_error": "❌ Ошибка перевода. Попробуйте позже",
        "no_text": "❌ Нет текста для перевода",
        "same_language": "ℹ️ Текст уже на целевом языке",
        "privacy_message": """🔒 **Политика конфиденциальности**

**Что мы логируем:**
• Запросы на перевод (без персональных данных)
• Сообщения об ошибках и системные события
• Статистику использования (анонимизированную)

**Что мы НЕ логируем:**
• Содержимое ваших личных сообщений
• ID пользователей или имена пользователей
• API ключи или токены

**Хранение данных:**
• Языковые предпочтения (можно удалить через /reset)
• Настройки канала (контролируются администратором)

**Для удаления ваших данных:**
Обратитесь к администратору бота.
""",
        "provider_info": "🔧 Текущий провайдер переводов: {provider}",
        "stats_message": """📊 **Статистика переводов**

**За последние 24 часа:**
• Переведено постов: {posts_24h}
• Всего переводов: {translations_24h}

**За последние 7 дней:**
• Переведено постов: {posts_7d}
• Всего переводов: {translations_7d}
""",
        "comments_disabled": "⚠️ Комментарии отключены для этого канала. Включите обсуждения для использования автоперевода.",
        "bot_not_admin": "⚠️ Мне нужны права администратора в этом канале для публикации комментариев.",
        "translation_header": "🌐 Перевод ({source}→{target}):",
        "translation_edited": "🌐 Перевод ({source}→{target}) (отредактировано):",
        "add_to_group": "➕ Добавить в группу",
        "add_to_channel": "📺 Добавить в канал",
        "setup_instructions": """📋 **Инструкция по настройке**

**Шаг 1: Добавьте бота в канал**
1. Зайдите в настройки канала
2. Нажмите "Администраторы"
3. Нажмите "Добавить администратора"
4. Найдите @{username}
5. Добавьте бота

**Шаг 2: Установите права бота (БЕЗОПАСНО)**
✅ **Включите только:**
• Права администратора (базовый уровень)

❌ **ВЫКЛЮЧИТЕ все остальные права:**
• Изменение описания
• Удаление сообщений
• Блокировка пользователей
• Пригласительные ссылки
• Закрепление сообщений
• Управление видеочатами
• Анонимность

**Шаг 3: Включите обсуждения**
1. Зайдите в настройки канала
2. Включите "Группа обсуждений"
3. Это позволит комментировать посты

**Шаг 4: Настройте языки**
Отправьте эту команду в канале:
`/set_channel_langs en,ru`

**Шаг 5: Протестируйте!**
Опубликуйте любое сообщение в канале - бот автоматически добавит перевод в комментариях!

🔒 **Безопасность**: Боту нужны только минимальные права для безопасной работы.""",
        "supported_languages": "🌐 **Поддерживаемые языки**: Английский, Русский, Турецкий, Испанский, Французский, Немецкий, Итальянский, Португальский, Китайский, Японский, Корейский, Арабский, Хинди, Голландский, Польский, Украинский и 120+ других языков!\n\n🛡️ **Примечание о безопасности**: Этот бот разработан с учетом приватности и безопасности. Ему нужны только минимальные права, и он никогда не сохраняет ваши сообщения.",
    }
}


def detect_user_language(text: str, user_id: Optional[int] = None) -> str:
    """Detect user's preferred language from text or user settings."""
    
    # Simple heuristic language detection
    if not text:
        return "en"
    
    # Check for Cyrillic characters (Russian/Ukrainian)
    if re.search(r'[а-яё]', text.lower()):
        return "ru"
    
    # Check for specific Turkish characters
    if re.search(r'[çğıöşü]', text.lower()):
        return "tr"
    
    # Check for Arabic script
    if re.search(r'[\u0600-\u06FF]', text):
        return "ar"
    
    # Check for Chinese characters
    if re.search(r'[\u4e00-\u9fff]', text):
        return "zh"
    
    # Check for Japanese characters
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return "ja"
    
    # Default to English
    return "en"


def detect_text_language(text: str) -> str:
    """Detect the language of the given text using simple heuristics."""
    
    if not text or len(text.strip()) < 3:
        return "en"
    
    text_lower = text.lower()
    
    # Count language-specific characters
    scores = {}
    
    # Cyrillic (Russian/Ukrainian)
    cyrillic_count = len(re.findall(r'[а-яё]', text_lower))
    if cyrillic_count > 0:
        scores["ru"] = cyrillic_count / len(text)
    
    # Turkish specific characters
    turkish_count = len(re.findall(r'[çğıöşü]', text_lower))
    if turkish_count > 0:
        scores["tr"] = turkish_count / len(text)
    
    # Arabic script
    arabic_count = len(re.findall(r'[\u0600-\u06FF]', text))
    if arabic_count > 0:
        scores["ar"] = arabic_count / len(text)
    
    # Chinese characters
    chinese_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    if chinese_count > 0:
        scores["zh"] = chinese_count / len(text)
    
    # Japanese characters
    japanese_count = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
    if japanese_count > 0:
        scores["ja"] = japanese_count / len(text)
    
    # German specific patterns
    if re.search(r'\b(der|die|das|und|ist|ein|eine)\b', text_lower):
        scores["de"] = scores.get("de", 0) + 0.1
    
    # French specific patterns
    if re.search(r'\b(le|la|les|et|est|un|une|de|du)\b', text_lower):
        scores["fr"] = scores.get("fr", 0) + 0.1
    
    # Spanish specific patterns
    if re.search(r'\b(el|la|los|las|y|es|un|una|de|del)\b', text_lower):
        scores["es"] = scores.get("es", 0) + 0.1
    
    # Italian specific patterns
    if re.search(r'\b(il|la|lo|gli|le|e|è|un|una|di|del)\b', text_lower):
        scores["it"] = scores.get("it", 0) + 0.1
    
    # Return language with highest score
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    
    # Default to English
    return "en"


def normalize_language_code(lang_code: str) -> Optional[str]:
    """Normalize and validate language code."""
    
    if not lang_code:
        return None
    
    # Convert to lowercase and take first 2 characters
    normalized = lang_code.lower().strip()[:2]
    
    # Check if it's a supported language
    supported_codes = [lang.value for lang in SupportedLanguage]
    
    if normalized in supported_codes:
        return normalized
    
    return None


def parse_language_list(lang_string: str) -> List[str]:
    """Parse comma-separated language list and validate codes."""
    
    if not lang_string:
        return []
    
    languages = []
    for lang in lang_string.split(","):
        normalized = normalize_language_code(lang.strip())
        if normalized and normalized not in languages:
            languages.append(normalized)
    
    return languages


def get_language_name(lang_code: str, display_lang: str = "en") -> str:
    """Get human-readable language name."""
    
    if lang_code in LANGUAGE_NAMES and display_lang in LANGUAGE_NAMES[lang_code]:
        return LANGUAGE_NAMES[lang_code][display_lang]
    
    return lang_code.upper()


def get_localized_string(key: str, lang: str = "en", **kwargs) -> str:
    """Get localized string with formatting."""
    
    # Fallback to English if language not supported
    if lang not in STRINGS:
        lang = "en"
    
    # Get string from dictionary
    if key not in STRINGS[lang]:
        # Fallback to English
        if key in STRINGS["en"]:
            text = STRINGS["en"][key]
        else:
            return f"Missing string: {key}"
    else:
        text = STRINGS[lang][key]
    
    # Format with provided arguments
    try:
        return text.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing format argument {e} for string {key}")
        return text


def extract_language_from_text(text: str) -> Tuple[Optional[str], str]:
    """Extract language code from text like 'переведи на en: текст'."""
    
    # Patterns to match language extraction
    patterns = [
        r'(?:переведи на|translate to|на)\s+([a-z]{2})\s*[:：]\s*(.+)',
        r'(?:to|на)\s+([a-z]{2})\s*[:：]\s*(.+)',
        r'^([a-z]{2})\s*[:：]\s*(.+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower().strip())
        if match:
            lang_code = normalize_language_code(match.group(1))
            remaining_text = match.group(2).strip()
            if lang_code and remaining_text:
                return lang_code, remaining_text
    
    return None, text


def get_supported_languages_list(display_lang: str = "en") -> str:
    """Get formatted list of supported languages."""
    
    languages = []
    for lang_code in [lang.value for lang in SupportedLanguage]:
        name = get_language_name(lang_code, display_lang)
        languages.append(f"{lang_code} - {name}")
    
    return "\n".join(languages)

