"""
Persistent user preferences (sprites, locale, theme). Loaded/saved as JSON.

redaction_symbol is used only by data_collector for dex text; it is not in Settings UI.
"""
from __future__ import annotations

import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "user_settings.json"
redaction_symbol = "???"

LOCALE_OPTIONS: list[tuple[str, str]] = [
    ("Brazilian portuguese", "pt-br"),
    ("Czech", "cs"),
    ("English", "en"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Japanese", "ja"),
    ("Japanese Hiragana and Katakana", "ja-hrkt"),
    ("Japanese romaji", "ja-roma"),
    ("Korean", "ko"),
    ("Simplified chinese", "zh-hans"),
    ("Spanish", "es"),
    ("Traditional chinese", "zh-hant"),
]
_LOCALE_CODES = {code for _, code in LOCALE_OPTIONS}

THEME_OPTIONS: list[tuple[str, str]] = [
    ("Light", "light"),
    ("Dark", "dark"),
]
_THEME_CODES = {code for _, code in THEME_OPTIONS}

SPRITE_OPTIONS: list[tuple[str, str]] = [
    ("Official Artwork", "other-official_artwork"),
    ("Pokémon Home", "other-home"),
    ("Dream World", "other-dream_world"),
    ("Showdown", "other-showdown"),
]
SPRITE_VARIANT_TO_KEYS: dict[str, list[str]] = {
    "other-official_artwork": ["other", "official-artwork", "front_default"],
    "other-home": ["other", "home", "front_default"],
    "other-dream_world": ["other", "dream_world", "front_default"],
    "other-showdown": ["other", "showdown", "front_default"],
}

DEFAULT_SPRITE_VARIANT = "other-home"
DEFAULT_LOCALE = "en"
DEFAULT_THEME = "light"

_data: dict[str, str] = {
    "sprites_variant": DEFAULT_SPRITE_VARIANT,
    "locale": DEFAULT_LOCALE,
    "theme": DEFAULT_THEME,
}


def load() -> None:
    global _data
    if not SETTINGS_PATH.is_file():
        return
    try:
        blob = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(blob, dict):
            if "sprites_variant" in blob:
                _data["sprites_variant"] = str(blob["sprites_variant"])
            if "locale" in blob:
                _data["locale"] = str(blob["locale"])
            if "theme" in blob:
                _data["theme"] = str(blob["theme"])
    except (OSError, json.JSONDecodeError, TypeError):
        pass


def save() -> None:
    try:
        SETTINGS_PATH.write_text(
            json.dumps(_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def get_locale() -> str:
    code = _data.get("locale", DEFAULT_LOCALE)
    if code in _LOCALE_CODES:
        return code
    return DEFAULT_LOCALE


def set_locale(code: str) -> None:
    if code in _LOCALE_CODES:
        _data["locale"] = code
        save()


def get_theme() -> str:
    t = _data.get("theme", DEFAULT_THEME)
    if t in _THEME_CODES:
        return t
    return DEFAULT_THEME


def set_theme(theme: str) -> None:
    if theme in _THEME_CODES:
        _data["theme"] = theme
        save()


def get_sprites_variant() -> str:
    v = _data.get("sprites_variant", DEFAULT_SPRITE_VARIANT)
    if v not in SPRITE_VARIANT_TO_KEYS:
        return DEFAULT_SPRITE_VARIANT
    return v


def set_sprites_variant(variant: str) -> None:
    if variant in SPRITE_VARIANT_TO_KEYS:
        _data["sprites_variant"] = variant
        save()


def get_sprite_path_keys() -> list[str]:
    return list(SPRITE_VARIANT_TO_KEYS[get_sprites_variant()])


load()

