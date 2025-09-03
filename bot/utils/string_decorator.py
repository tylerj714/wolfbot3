#! string_decorator.py
# Class with commands for formatting strings

from bot.cogs.emoji_manager import get_guild_emojis
from discord import Guild
import re


async def emoji_sub(text: str, emoji_map: dict[str, str], ignore_case=False):
    if not emoji_map:
        return text

    if ignore_case:
        def normalize_old(s):
            return s.lower()

        re_mode = re.IGNORECASE
    else:
        def normalize_old(s):
            return s

        re_mode = 0

    replacements: dict[str, str] = {normalize_old(key): val for key, val in emoji_map.items()}

    rep_sorted = sorted(replacements, key=len, reverse=True)
    rep_escaped = map(re.escape, rep_sorted)

    pattern = re.compile("|".join(rep_escaped), re_mode)

    return pattern.sub(lambda match: replacements[normalize_old(match.group(0))], text)

async def format_text(text: str, guild: Guild) -> str:

    formatted_text = await reformat_newline(text=text)
    emojified_text = await emojify(text=formatted_text, guild=guild)

    return emojified_text


async def reformat_newline(text: str) -> str:
    formatted_text = re.sub(r'\\.', lambda x: {'\\n': '\n'}.get(x[0], x[0]), text)

    return formatted_text


async def emojify(text: str, guild: Guild) -> str:
    guild_emojis = await get_guild_emojis(guild=guild)

    subbed_text = await emoji_sub(text=text, emoji_map=guild_emojis)

    return subbed_text
