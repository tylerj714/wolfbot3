# wolfbot2.py
import discord
import faulthandler
from discord.ext import commands
from discord import app_commands
from bot.botlogger.logging_manager import logger, log_info
from bot.model.conf_vars import ConfVars as Conf
from bot.cogs.action_views import ActionViewButtons
from bot.cogs.item_views import ItemViewButtons

class WolfBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all(), help_command=None)
        self.synced = False
        faulthandler.enable()

    async def setup_hook(self):
        # await self.load_extension(f"cogs.test")
        await self.load_extension(f"cogs.game_management")
        await self.load_extension(f"cogs.player_management")
        await self.load_extension(f"cogs.voting")
        # await self.load_extension(f"cogs.dice_rolling")
        await self.load_extension(f"cogs.resource_management")
        # await self.load_extension(f"cogs.attribute_management")
        await self.load_extension(f"cogs.action_item_management")
        await self.load_extension(f"cogs.action_views")
        await self.load_extension(f"cogs.item_views")
        # await self.load_extension(f"cogs.stat_mod_views")
        # await self.load_extension(f"cogs.persistent_view_management")
        await self.load_extension(f"cogs.moderator_request_management")
        await self.load_extension(f"cogs.emoji_manager")
        guild = discord.Object(id=Conf.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced_app_commands = await self.tree.sync(guild=guild)
        for command in synced_app_commands:
            log_info(f'Synced command: {command.name}')

    async def on_ready(self):
        await self.wait_until_ready()
        self.add_view(ActionViewButtons())
        self.add_view(ItemViewButtons())
        print(f"We have logged in as {self.user}.")


bot = WolfBot()


@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"Cooldown is in force, please wait for {round(error.retry_after)} seconds", ephemeral=True)
    else:
        raise error


def log_interaction_call(interaction: discord.Interaction):
    logger.info(
        f'Received command {interaction.command.name} with parameters {interaction.data} initiated by user {interaction.user.name}')


bot.run(Conf.TOKEN)
