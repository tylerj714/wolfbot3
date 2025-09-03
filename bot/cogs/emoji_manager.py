#! emoji_manager.py
# Class with slash commands for rolling dice

import discord
from discord.ext import commands
from discord import Guild
from bot.model.conf_vars import ConfVars as Conf
from bot.botlogger.logging_manager import log_info

guild_emoji_map = {}

async def populate_guild_emojis(guild: Guild) -> dict[str, str]:
    guild_emojis = guild.emojis

    for emoji in guild_emojis:
        guild_emoji_map[f":{emoji.name}:"] = f"<:{emoji.name}:{emoji.id}>"

    return guild_emoji_map

async def get_guild_emojis(guild: Guild) -> dict[str, str]:
    if not guild_emoji_map:
        log_info(f'Guild emoji map was not populated; repopulating now')
        await populate_guild_emojis(guild)
    return guild_emoji_map


class EmojiManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(Conf.GUILD_ID)
        await populate_guild_emojis(guild=guild)

        log_info(f'Custom Emoji mappings loaded for guild {guild.name}')


async def setup(bot: commands.Bot) -> None:
    cog = EmojiManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
