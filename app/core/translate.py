"""Translation service with multiple provider support."""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import httpx
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account

from .config import settings
from .logger import get_logger
from .i18n import detect_text_language, normalize_language_code

logger = get_logger(__name__)


@dataclass
class TranslationResult:
    """Translation result data class."""
    
    text: str
    source_lang: str
    target_lang: str
    provider: str
    confidence: Optional[float] = None
    detected_lang: Optional[str] = None


class TranslationError(Exception):
    """Base translation error."""
    pass


class ProviderError(TranslationError):
    """Provider-specific error."""
    pass


class RateLimitError(TranslationError):
    """Rate limit exceeded error."""
    pass


class BaseTranslationProvider(ABC):
    """Base class for translation providers."""
    
    def __init__(self, name: str):
        self.name = name
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    @abstractmethod
    async def translate(
        self, 
        text: str, 
        target_lang: str, 
        source_lang: Optional[str] = None
    ) -> TranslationResult:
        """Translate text to target language."""
        pass
    
    @abstractmethod
    async def detect_language(self, text: str) -> str:
        """Detect language of the text."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass


class DeepLProvider(BaseTranslationProvider):
    """DeepL translation provider."""
    
    def __init__(self):
        super().__init__("DeepL")
        self.api_key = settings.deepl_api_key
        self.base_url = "https://api-free.deepl.com/v2"  # Use free API by default
        
        # Language code mappings for DeepL
        self.lang_mapping = {
            "en": "EN",
            "ru": "RU",
            "tr": "TR",
            "es": "ES",
            "fr": "FR",
            "de": "DE",
            "it": "IT",
            "pt": "PT",
            "zh": "ZH",
            "ja": "JA",
            "ko": "KO",
            "nl": "NL",
            "pl": "PL",
            "uk": "UK",
        }
    
    def is_configured(self) -> bool:
        """Check if DeepL is configured."""
        return bool(self.api_key)
    
    def _map_language_code(self, lang_code: str, for_target: bool = False) -> str:
        """Map language code to DeepL format."""
        mapped = self.lang_mapping.get(lang_code, lang_code.upper())
        
        # DeepL requires specific codes for some target languages
        if for_target:
            if mapped == "EN":
                mapped = "EN-US"  # Default to US English
            elif mapped == "PT":
                mapped = "PT-PT"  # Default to European Portuguese
        
        return mapped
    
    async def detect_language(self, text: str) -> str:
        """Detect language using DeepL API."""
        if not self.client:
            raise ProviderError("Client not initialized")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/translate",
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                data={
                    "text": text[:1000],  # Limit text for detection
                    "target_lang": "EN",  # Required parameter
                }
            )
            
            if response.status_code == 429:
                raise RateLimitError("DeepL rate limit exceeded")
            elif response.status_code != 200:
                raise ProviderError(f"DeepL API error: {response.status_code}")
            
            result = response.json()
            if result.get("translations"):
                detected = result["translations"][0].get("detected_source_language", "").lower()
                return normalize_language_code(detected) or "en"
            
            return "en"
            
        except httpx.RequestError as e:
            logger.error(f"DeepL detection request failed: {e}")
            # Fallback to heuristic detection
            return detect_text_language(text)
    
    async def translate(
        self, 
        text: str, 
        target_lang: str, 
        source_lang: Optional[str] = None
    ) -> TranslationResult:
        """Translate text using DeepL."""
        if not self.client:
            raise ProviderError("Client not initialized")
        
        if not text.strip():
            raise TranslationError("Empty text provided")
        
        target_deepl = self._map_language_code(target_lang, for_target=True)
        
        data = {
            "text": text,
            "target_lang": target_deepl,
        }
        
        if source_lang:
            data["source_lang"] = self._map_language_code(source_lang)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/translate",
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                data=data
            )
            
            if response.status_code == 429:
                raise RateLimitError("DeepL rate limit exceeded")
            elif response.status_code != 200:
                raise ProviderError(f"DeepL API error: {response.status_code}")
            
            result = response.json()
            
            if not result.get("translations"):
                raise ProviderError("No translation returned from DeepL")
            
            translation = result["translations"][0]
            detected_lang = translation.get("detected_source_language", "").lower()
            
            return TranslationResult(
                text=translation["text"],
                source_lang=normalize_language_code(detected_lang) or source_lang or "auto",
                target_lang=target_lang,
                provider=self.name,
                detected_lang=normalize_language_code(detected_lang)
            )
            
        except httpx.RequestError as e:
            logger.error(f"DeepL translation request failed: {e}")
            raise ProviderError(f"DeepL request failed: {e}")


class GoogleTranslateProvider(BaseTranslationProvider):
    """Google Cloud Translate provider."""
    
    def __init__(self):
        super().__init__("Google Translate")
        self.project_id = settings.google_project_id
        self.credentials_path = settings.google_credentials_json_path
        self._translate_client = None
    
    def is_configured(self) -> bool:
        """Check if Google Translate is configured."""
        return bool(self.project_id and self.credentials_path)
    
    def _get_client(self):
        """Get Google Translate client."""
        if self._translate_client is None:
            if self.credentials_path and Path(self.credentials_path).exists():
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
                self._translate_client = translate.Client(credentials=credentials)
            else:
                # Try default credentials
                self._translate_client = translate.Client()
        
        return self._translate_client
    
    async def detect_language(self, text: str) -> str:
        """Detect language using Google Translate."""
        try:
            client = self._get_client()
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: client.detect_language(text[:1000])
            )
            
            detected = result.get("language", "en")
            return normalize_language_code(detected) or "en"
            
        except Exception as e:
            logger.error(f"Google Translate detection failed: {e}")
            return detect_text_language(text)
    
    async def translate(
        self, 
        text: str, 
        target_lang: str, 
        source_lang: Optional[str] = None
    ) -> TranslationResult:
        """Translate text using Google Translate."""
        if not text.strip():
            raise TranslationError("Empty text provided")
        
        try:
            client = self._get_client()
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: client.translate(
                    text,
                    target_language=target_lang,
                    source_language=source_lang
                )
            )
            
            detected_lang = result.get("detectedSourceLanguage")
            if detected_lang:
                detected_lang = normalize_language_code(detected_lang)
            
            return TranslationResult(
                text=result["translatedText"],
                source_lang=detected_lang or source_lang or "auto",
                target_lang=target_lang,
                provider=self.name,
                detected_lang=detected_lang
            )
            
        except Exception as e:
            logger.error(f"Google Translate failed: {e}")
            raise ProviderError(f"Google Translate failed: {e}")


class LibreTranslateProvider(BaseTranslationProvider):
    """LibreTranslate provider."""
    
    def __init__(self):
        super().__init__("LibreTranslate")
        self.base_url = settings.libre_base_url
        self.api_key = settings.libre_api_key
    
    def is_configured(self) -> bool:
        """Check if LibreTranslate is configured."""
        return bool(self.base_url)
    
    async def detect_language(self, text: str) -> str:
        """Detect language using LibreTranslate."""
        if not self.client:
            raise ProviderError("Client not initialized")
        
        try:
            data = {"q": text[:1000]}
            if self.api_key:
                data["api_key"] = self.api_key
            
            response = await self.client.post(
                f"{self.base_url}/detect",
                json=data
            )
            
            if response.status_code == 429:
                raise RateLimitError("LibreTranslate rate limit exceeded")
            elif response.status_code != 200:
                raise ProviderError(f"LibreTranslate API error: {response.status_code}")
            
            result = response.json()
            if result and len(result) > 0:
                detected = result[0].get("language", "en")
                return normalize_language_code(detected) or "en"
            
            return "en"
            
        except httpx.RequestError as e:
            logger.error(f"LibreTranslate detection failed: {e}")
            return detect_text_language(text)
    
    async def translate(
        self, 
        text: str, 
        target_lang: str, 
        source_lang: Optional[str] = None
    ) -> TranslationResult:
        """Translate text using LibreTranslate."""
        if not self.client:
            raise ProviderError("Client not initialized")
        
        if not text.strip():
            raise TranslationError("Empty text provided")
        
        # Auto-detect source language if not provided
        if not source_lang:
            source_lang = await self.detect_language(text)
        
        data = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
        }
        
        if self.api_key:
            data["api_key"] = self.api_key
        
        try:
            response = await self.client.post(
                f"{self.base_url}/translate",
                json=data
            )
            
            if response.status_code == 429:
                raise RateLimitError("LibreTranslate rate limit exceeded")
            elif response.status_code != 200:
                raise ProviderError(f"LibreTranslate API error: {response.status_code}")
            
            result = response.json()
            translated_text = result.get("translatedText", "")
            
            if not translated_text:
                raise ProviderError("No translation returned from LibreTranslate")
            
            return TranslationResult(
                text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                provider=self.name,
                detected_lang=source_lang if source_lang != "auto" else None
            )
            
        except httpx.RequestError as e:
            logger.error(f"LibreTranslate request failed: {e}")
            raise ProviderError(f"LibreTranslate request failed: {e}")


class MyMemoryProvider(BaseTranslationProvider):
    """MyMemory translation provider (free, but lower quality)."""
    
    def __init__(self):
        super().__init__("MyMemory")
        self.base_url = "https://api.mymemory.translated.net"
        # MyMemory has a limit of 10,000 words per request
        self.max_text_length = 10000
    
    def is_configured(self) -> bool:
        """MyMemory doesn't require configuration."""
        return True
    
    async def detect_language(self, text: str) -> str:
        """MyMemory doesn't have language detection, use heuristic."""
        return detect_text_language(text)
    
    async def translate(
        self, 
        text: str, 
        target_lang: str, 
        source_lang: Optional[str] = None
    ) -> TranslationResult:
        """Translate text using MyMemory."""
        if not self.client:
            raise ProviderError("Client not initialized")
        
        if not text.strip():
            raise TranslationError("Empty text provided")
        
        # Truncate text if too long
        if len(text) > self.max_text_length:
            text = text[:self.max_text_length]
            logger.warning(f"Text truncated to {self.max_text_length} characters for MyMemory")
        
        # Auto-detect source language if not provided
        if not source_lang:
            source_lang = await self.detect_language(text)
        
        try:
            response = await self.client.get(
                f"{self.base_url}/get",
                params={
                    "q": text,
                    "langpair": f"{source_lang}|{target_lang}"
                },
                timeout=30.0
            )
            
            if response.status_code == 429:
                raise RateLimitError("MyMemory rate limit exceeded")
            elif response.status_code != 200:
                raise ProviderError(f"MyMemory API error: {response.status_code}")
            
            result = response.json()
            
            if result.get("responseStatus") != 200:
                error_details = result.get("responseDetails", "Unknown error")
                # Handle common MyMemory errors
                if "QUERY_LENGTH" in error_details:
                    raise ProviderError("Text too long for MyMemory (max 10,000 words)")
                raise ProviderError(f"MyMemory error: {error_details}")
            
            translated_text = result["responseData"]["translatedText"]
            
            if not translated_text or translated_text == text:
                # If translation is same as original, might be an error
                logger.warning(f"MyMemory returned same text, might be an error")
            
            return TranslationResult(
                text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                provider=self.name,
                detected_lang=source_lang if source_lang != "auto" else None
            )
            
        except httpx.RequestError as e:
            logger.error(f"MyMemory request failed: {e}")
            raise ProviderError(f"MyMemory request failed: {e}")


class ArgosTranslateProvider(BaseTranslationProvider):
    """Argos Translate provider (open-source, free, good quality)."""
    
    def __init__(self):
        super().__init__("Argos Translate")
        # Use public Argos Translate API server
        self.base_url = "https://translate.argosopentech.com"
    
    def is_configured(self) -> bool:
        """Argos Translate doesn't require configuration."""
        return True
    
    async def detect_language(self, text: str) -> str:
        """Argos Translate doesn't have language detection, use heuristic."""
        return detect_text_language(text)
    
    async def translate(
        self, 
        text: str, 
        target_lang: str, 
        source_lang: Optional[str] = None
    ) -> TranslationResult:
        """Translate text using Argos Translate."""
        if not self.client:
            raise ProviderError("Client not initialized")
        
        if not text.strip():
            raise TranslationError("Empty text provided")
        
        # Auto-detect source language if not provided
        if not source_lang:
            source_lang = await self.detect_language(text)
        
        # Argos Translate uses language codes like "en", "ru", etc.
        # Format: source-target
        lang_pair = f"{source_lang}-{target_lang}"
        
        try:
            response = await self.client.post(
                f"{self.base_url}/translate",
                json={
                    "q": text,
                    "source": source_lang,
                    "target": target_lang,
                    "format": "text"
                },
                timeout=30.0
            )
            
            if response.status_code == 429:
                raise RateLimitError("Argos Translate rate limit exceeded")
            elif response.status_code != 200:
                error_text = response.text[:200] if response.text else "Unknown error"
                raise ProviderError(f"Argos Translate API error: {response.status_code} - {error_text}")
            
            result = response.json()
            translated_text = result.get("translatedText", "")
            
            if not translated_text:
                raise ProviderError("No translation returned from Argos Translate")
            
            return TranslationResult(
                text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                provider=self.name,
                detected_lang=source_lang if source_lang != "auto" else None
            )
            
        except httpx.RequestError as e:
            logger.error(f"Argos Translate request failed: {e}")
            raise ProviderError(f"Argos Translate request failed: {e}")


class TranslationService:
    """Main translation service with multiple provider support."""
    
    def __init__(self):
        self.providers: Dict[str, BaseTranslationProvider] = {
            "DEEPL": DeepLProvider(),
            "GOOGLE": GoogleTranslateProvider(),
            "LIBRE": LibreTranslateProvider(),
            "MYMEMORY": MyMemoryProvider(),
            "ARGOS": ArgosTranslateProvider(),
        }
        self.primary_provider = settings.translator_provider
        # Order fallback providers by quality (best first)
        fallback_order = ["ARGOS", "DEEPL", "LIBRE", "GOOGLE", "MYMEMORY"]
        self.fallback_providers = [
            name for name in fallback_order 
            if name != self.primary_provider and name in self.providers
        ]
    
    def get_available_providers(self) -> List[str]:
        """Get list of configured providers."""
        return [
            name for name, provider in self.providers.items()
            if provider.is_configured()
        ]
    
    async def translate(
        self, 
        text: str, 
        target_lang: str, 
        source_lang: Optional[str] = None,
        max_retries: int = 2
    ) -> TranslationResult:
        """Translate text with fallback support."""
        
        if not text or not text.strip():
            raise TranslationError("Empty text provided")
        
        # Normalize language codes
        target_lang = normalize_language_code(target_lang)
        if not target_lang:
            raise TranslationError("Invalid target language code")
        
        if source_lang:
            source_lang = normalize_language_code(source_lang)
        
        # Detect source language if not provided
        if not source_lang:
            source_lang = await self.detect_language(text)
        
        # Check if translation is needed
        if source_lang == target_lang:
            return TranslationResult(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                provider="none",
                detected_lang=source_lang
            )
        
        # Try primary provider first
        providers_to_try = [self.primary_provider] + self.fallback_providers
        
        for provider_name in providers_to_try:
            provider = self.providers.get(provider_name)
            
            if not provider or not provider.is_configured():
                continue
            
            for attempt in range(max_retries + 1):
                try:
                    async with provider:
                        result = await provider.translate(text, target_lang, source_lang)
                        logger.info(f"Translation successful with {provider_name}")
                        return result
                        
                except RateLimitError:
                    logger.warning(f"{provider_name} rate limit exceeded")
                    break  # Don't retry rate limits, try next provider
                    
                except ProviderError as e:
                    logger.warning(f"{provider_name} failed (attempt {attempt + 1}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
                except Exception as e:
                    logger.error(f"Unexpected error with {provider_name}: {e}")
                    break
        
        raise TranslationError("All translation providers failed")
    
    async def detect_language(self, text: str) -> str:
        """Detect language with provider fallback."""
        
        # Try primary provider first
        provider = self.providers.get(self.primary_provider)
        
        if provider and provider.is_configured():
            try:
                async with provider:
                    return await provider.detect_language(text)
            except Exception as e:
                logger.warning(f"Language detection failed with {self.primary_provider}: {e}")
        
        # Fallback to heuristic detection
        return detect_text_language(text)
    
    async def translate_multiple(
        self, 
        text: str, 
        target_langs: List[str], 
        source_lang: Optional[str] = None
    ) -> List[TranslationResult]:
        """Translate text to multiple target languages."""
        
        results = []
        
        # Detect source language once
        if not source_lang:
            source_lang = await self.detect_language(text)
        
        # Filter out same language
        target_langs = [
            lang for lang in target_langs 
            if normalize_language_code(lang) != source_lang
        ]
        
        # Translate to each target language
        for target_lang in target_langs:
            try:
                result = await self.translate(text, target_lang, source_lang)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to translate to {target_lang}: {e}")
                # Continue with other languages
        
        return results


# Global translation service instance
translation_service = TranslationService()
