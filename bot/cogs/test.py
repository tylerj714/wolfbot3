#! test.py
# Simple test and template cog class

import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from bot.model.conf_vars import ConfVars as Conf

class Test(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="test",
                          description="Testing cog functionality for discord bot")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message("Test success", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Test(bot), guilds=[discord.Object(id=Conf.GUILD_ID)])
