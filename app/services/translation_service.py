import asyncio
from googletrans import Translator


async def translate_text(text: str, target_lang: str = "en", source_lang: str = "auto") -> str:
    if not text.strip():
        return ""

    async with Translator() as translator:
        try:
            result = await translator.translate(text, src=source_lang, dest=target_lang)
            return result.text
        except Exception as e:
            return f"❌ Ошибка перевода: {e}"
