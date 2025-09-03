#! resource_management.py
# Class with slash commands managing resources

import discord
from discord import app_commands
from discord.ext import commands
from bot.model.conf_vars import ConfVars as Conf
import bot.model.data_model as gdm
from bot.botlogger.logging_manager import log_interaction_call, log_info
from bot.utils.command_autocompletes import player_list_autocomplete, resource_type_autocomplete
from bot.utils.message_formatter import *


class ResourceManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="resource-trigger-daily-incomes",
                          description="Triggers the daily incomes for resources")
    @app_commands.default_permissions(manage_guild=True)
    async def resource_trigger_daily_incomes(self,
                                             interaction: discord.Interaction):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_players = game.players

        for game_player in game_players:
            player_moderation_channel = await guild.fetch_channel(game_player.player_mod_channel)
            for player_resource in game_player.player_resources:
                if player_resource.is_perishable:
                    if player_resource.resource_amt > 0:
                        # notify player how much of a resource they lost due to expiration
                        expiration_responses = await construct_resource_modified_display(action='expired',
                                                                                         player_resource=player_resource,
                                                                                         res_change_amt=player_resource.resource_amt,
                                                                                         game=game,
                                                                                         guild=guild)
                        if player_moderation_channel:
                            for expiration_response in expiration_responses:
                                await player_moderation_channel.send(expiration_response)

                    player_resource.resource_amt = 0
                if player_resource.resource_income and player_resource.resource_income > 0:
                    player_resource.resource_amt += player_resource.resource_income
                    if player_resource.resource_amt > player_resource.resource_max:
                        player_resource.resource_amt = player_resource.resource_max
                    income_responses = await construct_resource_modified_display(action='income',
                                                                                 player_resource=player_resource,
                                                                                 res_change_amt=player_resource.resource_income,
                                                                                 game=game,
                                                                                 guild=guild)
                    if player_moderation_channel:
                        for income_response in income_responses:
                            await player_moderation_channel.send(income_response)

        # save game information
        await gdm.write_game(game)

        # Notify player of new resource totals
        for game_player in game_players:
            player_moderation_channel = await guild.fetch_channel(game_player.player_mod_channel)
            if player_moderation_channel:
                display_responses = await construct_player_resources_display(player=game_player,
                                                                             game=game,
                                                                             guild=guild)
                for display_response in display_responses:
                    await player_moderation_channel.send(display_response)

    @app_commands.command(name="resource-player-view",
                          description="Generates a display of the chosen player's resources")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    async def resource_player_view(self,
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

        player_resource_responses = await construct_player_resources_display(player=game_player, game=game, guild=guild)

        for response in player_resource_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="resource-player-view-all",
                          description="Generates a display of all player's resources")
    @app_commands.default_permissions(manage_guild=True)
    async def resource_player_view_all(self,
                                   interaction: discord.Interaction):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild
        game_players = game.players

        if not game_players:
            await interaction.followup.send(f'No players found for this game!')
            return

        player_resource_responses = await construct_player_resources_display_table(players=game_players,
                                                                                   game=game,
                                                                                   guild=guild)

        for response in player_resource_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="resource-view",
                          description="Generates a display of your current resources")
    async def resource_view(self,
                            interaction: discord.Interaction):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(interaction.user.id)

        if not game_player:
            await interaction.followup.send(f'You are not a registered player for this game!')
            return

        player_resource_responses = await construct_player_resources_display(player=game_player, game=game, guild=guild)

        for response in player_resource_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="resource-player-add",
                          description="Adds an amount of resources to a chosen player")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(resource_type=resource_type_autocomplete)
    async def resource_player_add(self,
                                  interaction: discord.Interaction,
                                  player: str,
                                  resource_type: str,
                                  resource_amt: app_commands.Range[int, 1, 100]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))
        resource_to_modify = game_player.get_resource(resource_type)

        if resource_to_modify is None:
            await interaction.followup.send(
                f'Resource {resource_type} not defined for player {game_player.player_discord_name}!',
                ephemeral=True)
            return

        game_player.modify_resource(resource_name=resource_type, amt=resource_amt)

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Added {resource_amt} of resource {resource_type} to player '
                                        f'{game_player.player_discord_name}!', ephemeral=True)

        game_player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None

        resource_modified_response = await construct_resource_modified_display(action='gained',
                                                                               player_resource=resource_to_modify,
                                                                               res_change_amt=resource_amt,
                                                                               guild=guild,
                                                                               game=game)

        if game_player_mod_channel is not None:
            for resource_modified_response in resource_modified_response:
                await game_player_mod_channel.send(f'{resource_modified_response}')

    @app_commands.command(name="resource-player-remove",
                          description="Removes an amount of resources from a chosen player")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(resource_type=resource_type_autocomplete)
    async def resource_player_remove(self,
                                     interaction: discord.Interaction,
                                     player: str,
                                     resource_type: str,
                                     resource_amt: app_commands.Range[int, 1, 100]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))
        resource_to_modify = game_player.get_resource(resource_type)

        if resource_to_modify is None:
            await interaction.followup.send(
                f'Resource {resource_type} not defined for player {game_player.player_discord_name}!',
                ephemeral=True)
            return

        game_player.modify_resource(resource_name=resource_type, amt=-resource_amt)

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Removed {resource_amt} of resource {resource_type} from player '
                                        f'{game_player.player_discord_name}!', ephemeral=True)

        game_player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None

        resource_modified_response = await construct_resource_modified_display(action='lost',
                                                                               player_resource=resource_to_modify,
                                                                               res_change_amt=resource_amt,
                                                                               guild=guild,
                                                                               game=game)

        if game_player_mod_channel is not None:
            for resource_modified_response in resource_modified_response:
                await game_player_mod_channel.send(f'{resource_modified_response}')

    @app_commands.command(name="resource-player-transfer",
                          description="Transfers an amount of resources from one player to another player")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(recipient_player=player_list_autocomplete)
    @app_commands.autocomplete(resource_type=resource_type_autocomplete)
    async def resource_player_transfer(self,
                                       interaction: discord.Interaction,
                                       player: str,
                                       recipient_player: str,
                                       resource_type: str,
                                       resource_amt: app_commands.Range[int, 1, 100]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        sending_player = game.get_player(int(player))
        receiving_player = game.get_player(int(recipient_player))

        resource_to_send = sending_player.get_resource(resource_type)

        if resource_to_send is None:
            await interaction.followup.send(
                f'Resource {resource_type} not defined for player {sending_player.player_discord_name}!',
                ephemeral=True)
            return
        if not resource_to_send.is_commodity:
            await interaction.followup.send(f'Resource {resource_type} is not defined as a commodity! Cannot transfer '
                                            f'non-commodity resources!', ephemeral=True)
            return
        if resource_amt > resource_to_send.resource_amt:
            await interaction.followup.send(
                f'Resource Amount {resource_amt} exceeds available amount of {resource_to_send.resource_amt} for player '
                f'{sending_player.player_discord_name}!', ephemeral=True)
            return
        if receiving_player is None:
            await interaction.followup.send(f'Recipient player was not a valid choice!', ephemeral=True)
            return

        sending_player.modify_resource(resource_name=resource_type, amt=-resource_amt)
        receiving_player.modify_resource(resource_name=resource_type, amt=resource_amt)

        sent_resource = sending_player.get_resource(resource_name=resource_type)
        received_resource = receiving_player.get_resource(resource_name=resource_type)

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Sent {resource_amt} of resource {resource_type} from player '
                                        f'{sending_player.player_discord_name} to player '
                                        f'{receiving_player.player_discord_name}!', ephemeral=True)

        sending_player_mod_channel = await interaction.guild.fetch_channel(
            sending_player.player_mod_channel) if sending_player.player_mod_channel is not None else None
        receiving_player_mod_channel = await interaction.guild.fetch_channel(
            receiving_player.player_mod_channel) if receiving_player.player_mod_channel is not None else None

        resource_sent_formatted_responses = await construct_resource_modified_display(action='sent',
                                                                                      player_resource=sent_resource,
                                                                                      res_change_amt=resource_amt,
                                                                                      guild=guild,
                                                                                      game=game)
        resource_received_formatted_responses = await construct_resource_modified_display(action='received',
                                                                                          player_resource=received_resource,
                                                                                          res_change_amt=resource_amt,
                                                                                          guild=guild,
                                                                                          game=game)

        if sending_player_mod_channel is not None:
            for resource_sent_response in resource_sent_formatted_responses:
                await sending_player_mod_channel.send(f'{resource_sent_response}')
        if receiving_player_mod_channel is not None:
            for resource_received_response in resource_received_formatted_responses:
                await receiving_player_mod_channel.send(f'{resource_received_response}')

    @app_commands.command(name="resource-transfer",
                          description="Transfers an amount of the chosen resource to another player")
    @app_commands.autocomplete(recipient_player=player_list_autocomplete)
    @app_commands.autocomplete(resource_type=resource_type_autocomplete)
    async def resource_transfer(self,
                                interaction: discord.Interaction,
                                recipient_player: str,
                                resource_type: str,
                                resource_amt: app_commands.Range[int, 1, 100]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        if not game.is_active:
            await interaction.followup.send(
                f'The bot has been put in an inactive state by the moderator. Please try again later.', ephemeral=True)
            return

        if game.resources_locked:
            await interaction.followup.send(f'The game moderator has locked resource transferring at this time!')
            return

        sending_player = game.get_player(int(interaction.user.id))
        receiving_player = game.get_player(int(recipient_player))

        if not sending_player:
            await interaction.followup.send(f'You are not a registered player for this game!')
            return
        if sending_player.is_dead:
            await interaction.followup.send(f'You are currently dead and cannot transfer resources!')
            return

        resource_to_send = sending_player.get_resource(resource_type)

        if resource_to_send is None:
            await interaction.followup.send(
                f'Resource {resource_type} not defined for player {sending_player.player_discord_name}!',
                ephemeral=True)
            return
        if not resource_to_send.is_commodity:
            await interaction.followup.send(f'Resource {resource_type} is not defined as a commodity! Cannot transfer '
                                            f'non-commodity resources!', ephemeral=True)
            return
        if resource_amt > resource_to_send.resource_amt:
            await interaction.followup.send(
                f'Resource Amount {resource_amt} exceeds available amount of {resource_to_send.resource_amt} for player '
                f'{sending_player.player_discord_name}!', ephemeral=True)
            return
        if receiving_player is None:
            await interaction.followup.send(f'Recipient player was not a valid choice!', ephemeral=True)
            return

        sending_player.modify_resource(resource_name=resource_type, amt=-resource_amt)
        receiving_player.modify_resource(resource_name=resource_type, amt=resource_amt)

        sent_resource = sending_player.get_resource(resource_name=resource_type)
        received_resource = receiving_player.get_resource(resource_name=resource_type)

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Sent {resource_amt} of resource {resource_type} from player '
                                        f'{sending_player.player_discord_name} to player '
                                        f'{receiving_player.player_discord_name}!', ephemeral=True)

        sending_player_mod_channel = await interaction.guild.fetch_channel(
            sending_player.player_mod_channel) if sending_player.player_mod_channel is not None else None
        receiving_player_mod_channel = await interaction.guild.fetch_channel(
            receiving_player.player_mod_channel) if receiving_player.player_mod_channel is not None else None

        resource_sent_formatted_responses = await construct_resource_modified_display(action='sent',
                                                                                      player_resource=sent_resource,
                                                                                      res_change_amt=resource_amt,
                                                                                      guild=guild,
                                                                                      game=game)
        resource_received_formatted_responses = await construct_resource_modified_display(action='received',
                                                                                          player_resource=received_resource,
                                                                                          res_change_amt=resource_amt,
                                                                                          guild=guild,
                                                                                          game=game)

        if sending_player_mod_channel is not None:
            for resource_sent_response in resource_sent_formatted_responses:
                await sending_player_mod_channel.send(f'{resource_sent_response}')
        if receiving_player_mod_channel is not None:
            for resource_received_response in resource_received_formatted_responses:
                await receiving_player_mod_channel.send(f'{resource_received_response}')


async def setup(bot: commands.Bot) -> None:
    cog = ResourceManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
