#! attribute_management.py
# Class with slash commands managing attributes

import discord
from discord import app_commands
from discord.ext import commands
from bot.model.conf_vars import ConfVars as Conf
import bot.model.data_model as gdm
from bot.botlogger.logging_manager import log_interaction_call, log_info
from bot.utils.command_autocompletes import player_list_autocomplete, attribute_type_autocomplete
from bot.utils.message_formatter import *


class AttributeManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="attribute-player-view",
                          description="Generates a display of the chosen player's attributes")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    async def attribute_player_view(self,
                                    interaction: discord.Interaction,
                                    player: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))

        if not game_player:
            await interaction.followup.send(f'The selected player is not a registered player for this game!')
            return

        player_attribute_responses = await construct_player_attributes_display(player=game_player, game=game,
                                                                               guild=guild)

        for response in player_attribute_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="attribute-player-view-all",
                          description="Generates a display of the chosen player's attributes")
    @app_commands.default_permissions(manage_guild=True)
    async def attribute_player_view_all(self,
                                        interaction: discord.Interaction):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild
        game_players = game.players

        if not game_players:
            await interaction.followup.send(f'No players found for this game!')
            return

        player_attribute_responses = await construct_player_attributes_display_table(players=game_players,
                                                                                     game=game,
                                                                                     guild=guild)
        for response in player_attribute_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="attribute-view",
                          description="Generates a display of your current attributes")
    async def attribute_view(self,
                             interaction: discord.Interaction):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(interaction.user.id)

        if not game_player:
            await interaction.followup.send(f'You are not a registered player for this game!')
            return

        player_attribute_responses = await construct_player_attributes_display(player=game_player, game=game,
                                                                               guild=guild)

        for response in player_attribute_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="attribute-player-add",
                          description="Adds an amount of attributes to a chosen player")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(attribute_type=attribute_type_autocomplete)
    async def attribute_player_add(self,
                                   interaction: discord.Interaction,
                                   player: str,
                                   attribute_type: str,
                                   attribute_amt: app_commands.Range[int, 1, 100]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))
        attribute_to_modify = game_player.get_attribute(attribute_type)

        if attribute_to_modify is None:
            await interaction.followup.send(
                f'Attribute {attribute_type} not defined for player {game_player.player_discord_name}!',
                ephemeral=True)
            return

        game_player.modify_attribute(attribute_name=attribute_type, amt=attribute_amt)

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Player attribute {attribute_type} increased by {attribute_amt} for '
                                        f'{game_player.player_discord_name}!', ephemeral=True)

        game_player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None

        attribute_modified_response = await construct_attribute_modified_display(action='increased',
                                                                                 player_attribute=attribute_to_modify,
                                                                                 att_change_amt=attribute_amt,
                                                                                 guild=guild,
                                                                                 game=game)

        if game_player_mod_channel is not None:
            for attribute_modified_response in attribute_modified_response:
                await game_player_mod_channel.send(f'{attribute_modified_response}')

    @app_commands.command(name="attribute-player-remove",
                          description="Removes an amount of an attribute from a chosen player")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(attribute_type=attribute_type_autocomplete)
    async def attribute_player_remove(self,
                                      interaction: discord.Interaction,
                                      player: str,
                                      attribute_type: str,
                                      attribute_amt: app_commands.Range[int, 1, 100]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))
        attribute_to_modify = game_player.get_attribute(attribute_type)

        if attribute_to_modify is None:
            await interaction.followup.send(
                f'Attribute {attribute_type} not defined for player {game_player.player_discord_name}!',
                ephemeral=True)
            return

        game_player.modify_attribute(attribute_name=attribute_type, amt=-attribute_amt)

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Player attribute {attribute_type} decreased by {attribute_amt} for '
                                        f'{game_player.player_discord_name}!', ephemeral=True)

        game_player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None

        attribute_modified_response = await construct_attribute_modified_display(action='decreased',
                                                                                 player_attribute=attribute_to_modify,
                                                                                 att_change_amt=attribute_amt,
                                                                                 guild=guild,
                                                                                 game=game)

        if game_player_mod_channel is not None:
            for attribute_modified_response in attribute_modified_response:
                await game_player_mod_channel.send(f'{attribute_modified_response}')


async def setup(bot: commands.Bot) -> None:
    cog = AttributeManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
