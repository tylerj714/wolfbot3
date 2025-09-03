import discord
from discord import app_commands
from discord.ext import commands
from bot.model.conf_vars import ConfVars as Conf
import bot.model.data_model as gdm
from bot.model.data_model import PersistentInteractableView
from bot.botlogger.logging_manager import log_interaction_call, log_info
from bot.utils.command_autocompletes import persistent_view_autocomplete


class PersistentViewManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="delete-persistent-view",
                          description="Creates a persistent view of actions that can be filtered using buttons")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(view_name=persistent_view_autocomplete)
    async def delete_persistent_view(self,
                                     interaction: discord.Interaction,
                                     view_name: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        pi_view: PersistentInteractableView = game.get_pi_view(view_name)

        if not pi_view:
            interaction.response.send_message(f"No persistent view with name {view_name} could be found!")
            return

        view_channel = await guild.fetch_channel(pi_view.channel_id)
        if not view_channel:
            interaction.response.send_message(f"Problem retrieving channel from guild with id {pi_view.channel_id}!")
            return

        for message_id in pi_view.message_ids:
            msg = await view_channel.fetch_message(message_id)
            if msg:
                await msg.delete()

        # Remove the persistent view from the game object by name
        game.remove_pi_view(view_name)
        await gdm.write_game(game)

        await interaction.followup.send(f'Deleted persistent view {view_name}!')


async def setup(bot: commands.Bot) -> None:
    cog = PersistentViewManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
