#! player_management.py
# Class with slash commands for managing players

import discord
from discord import app_commands
from discord.ext import commands
from bot.model.conf_vars import ConfVars as Conf
from bot.model.data_model import Game, Player, Round, Vote, Party, Dilemma
from typing import Literal, Optional
import bot.model.data_model as gdm
from bot.botlogger.logging_manager import log_interaction_call, log_info
from bot.utils.command_autocompletes import player_list_autocomplete, party_list_autocomplete
from bot.cogs.moderator_request_management import send_message_to_moderator as modmsg
import random
import string


class PlayerManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="add-player",
                          description="Adds a player to the game, creating a private moderator channel for them in the process.")
    @app_commands.default_permissions(manage_guild=True)
    async def add_player(self,
                         interaction: discord.Interaction,
                         player: discord.Member,
                         channel_name: str):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        if game.get_player(player.id) is None:

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                player: discord.PermissionOverwrite(read_messages=True)
            }

            category_channel = await interaction.guild.fetch_channel(Conf.MOD_CATEGORY)
            mod_channel = await interaction.guild.create_text_channel(name=channel_name, overwrites=overwrites,
                                                                      category=category_channel)

            new_player = Player(player_id=player.id,
                                player_discord_name=player.name,
                                player_mod_channel=mod_channel.id,
                                player_attributes=[],
                                player_actions=[])
            game.add_player(new_player)
            await gdm.write_game(game=game)
            await interaction.response.send_message(f'Added player {player.name} to game!', ephemeral=True)
        else:
            await interaction.response.send_message(f'Failed to add {player.name} to game!', ephemeral=True)

    @app_commands.command(name="kill-player",
                          description="Toggles a player status of being dead or not.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    async def kill_player(self,
                          interaction: discord.Interaction,
                          player: str,
                          dead: Literal['True', 'False']):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        this_player = game.get_player(int(player))
        if this_player is None:
            await interaction.response.send_message(f'The selected player is not currently defined in this game!',
                                                    ephemeral=True)
        else:
            this_player.is_dead = True if dead == 'True' else False

            await gdm.write_game(game=game)
            await interaction.response.send_message(f'Set alive status of {this_player.player_discord_name} to {dead}!',
                                                    ephemeral=True)

    # @app_commands.command(name="open-private-chat",
    #                       description="Opens a private chat with the chosen player")
    # @app_commands.autocomplete(player=player_list_autocomplete)
    # async def open_private_chat(self,
    #                             interaction: discord.Interaction,
    #                             player: Optional[str] = None):
    #     log_interaction_call(interaction)
    #     game = await gdm.get_game(file_path=Conf.GAME_PATH)
    #
    #     guild = interaction.guild
    #     discord_user1 = interaction.user
    #     player2 = game.get_player(int(player))
    #     discord_user2 = await guild.fetch_member(player2.player_id)
    #     channel_identifier = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    #     category_channel = await guild.fetch_channel(Conf.PRIVATE_CHAT_CATEGORY)
    #
    #     overwrites = {
    #         interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
    #         discord_user1: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    #         discord_user2: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    #     }
    #
    #     private_channel = await guild.create_text_channel(name=f'private-chat-{channel_identifier}',
    #                                                       overwrites=overwrites, category=category_channel)
    #     await interaction.response.send_message(f'Created private channel with player {player2.player_discord_name}')
    #     await private_channel.send(
    #         f'Your private chat between {discord_user1.mention} and {discord_user2.mention} has begun!')

    @app_commands.command(name="create-party",
                          description="Creates a player party group")
    @app_commands.default_permissions(manage_guild=True)
    async def create_party(self, interaction: discord.Interaction,
                           party_name: str,
                           party_max_size: int):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        guild = interaction.guild
        category_channel = await guild.fetch_channel(Conf.PRIVATE_CHAT_CATEGORY)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }

        party_channel = await guild.create_text_channel(name=f'party-{party_name}', overwrites=overwrites,
                                                        category=category_channel)

        party = Party(player_ids=set(), max_size=party_max_size, channel_id=party_channel.id, party_name=party_name)
        game.add_party(party)

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'Created new party {party_name}!', ephemeral=True)

    @app_commands.command(name="add-party-player",
                          description="Adds a player to a party and manages text channel permissions")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(party=party_list_autocomplete)
    async def add_party_player(self, interaction: discord.Interaction,
                               party: str,
                               player: str):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game_party = game.get_party(int(party))
        game_player = game.get_player(int(player))

        if game_party is None:
            await interaction.response.send_message(f'Could not find a party with that identifier!', ephemeral=True)
            return

        if game_player is None:
            await interaction.response.send_message(f'Could not find a player with that identifier!', ephemeral=True)
            return

        if game_party.max_size != -1 and len(game_party.player_ids) >= game_party.max_size:
            await interaction.response.send_message(f'Party size is already at max size of {game_party.max_size}!',
                                                    ephemeral=True)
            return

        guild = interaction.guild
        party_channel = await guild.fetch_channel(game_party.channel_id)
        player_user = await guild.fetch_member(game_player.player_id)

        existing_party = game.get_player_party(game_player)

        if existing_party is not None:
            existing_party_channel = await guild.fetch_channel(existing_party.channel_id)
            await existing_party_channel.set_permissions(player_user, read_messages=False, send_messages=False,
                                                         read_message_history=False)
            await existing_party_channel.send(f'**{game_player.player_discord_name}** has left {existing_party.party_name}!')
            existing_party.remove_player(game_player)

        game_party.add_player(game_player)

        await party_channel.set_permissions(player_user, read_messages=True, send_messages=True,
                                            read_message_history=True)

        await gdm.write_game(game=game)
        await interaction.response.send_message(
            f'Added player {game_player.player_discord_name} to party {game_party.party_name}!', ephemeral=True)
        await party_channel.send(f'**{game_player.player_discord_name}** has joined {game_party.party_name}!')

    @app_commands.command(name="remove-party-player",
                          description="Removes a player from a party and manages text channel permissions")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    async def remove_party_player(self, interaction: discord.Interaction,
                                  player: str):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game_player = game.get_player(int(player))

        if game_player is None:
            await interaction.response.send_message(f'Could not find a player with that identifier!', ephemeral=True)
            return

        game_party = game.get_player_party(game_player)

        if game_party is None:
            await interaction.response.send_message(
                f'Player {game_player.player_discord_name} is not a member of any current party!', ephemeral=True)
            return

        guild = interaction.guild
        party_channel = await guild.fetch_channel(game_party.channel_id)
        player_user = await guild.fetch_member(game_player.player_id)

        game_party.remove_player(game_player)

        await party_channel.set_permissions(player_user, read_messages=False, send_messages=False,
                                            read_message_history=False)

        await gdm.write_game(game=game)
        await interaction.response.send_message(
            f'Removed player {game_player.player_discord_name} from party {game_party.party_name}!', ephemeral=True)
        await party_channel.send(f'**{game_player.player_discord_name}** has left {game_party.party_name}!')

    @app_commands.command(name="join-party",
                          description="Allows a player to join a party and manages text channel permissions")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    @app_commands.autocomplete(party=party_list_autocomplete)
    async def join_party(self, interaction: discord.Interaction,
                         party: str):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game_party = game.get_party(int(party))
        game_player = game.get_player(interaction.user.id)

        if not game.is_active:
            await interaction.response.send_message(
                f'The bot has been put in an inactive state by the moderator. Please try again later.', ephemeral=True)
            return
        elif game.parties_locked:
            await interaction.response.send_message(f'Parties are currently locked.', ephemeral=True)
            return

        if game_party is None:
            await interaction.response.send_message(f'Could not find a party with that identifier!', ephemeral=True)
            return

        if game_player is None:
            await interaction.response.send_message(f'You are not a registered player of the current game!',
                                                    ephemeral=True)
            return

        if game_player.is_dead:
            await interaction.response.send_message(f'You are dead! Begone apparition!', ephemeral=True)
            return

        if game_party.max_size != -1 and len(game_party.player_ids) >= game_party.max_size:
            await interaction.response.send_message(f'Party size is already at max size of {game_party.max_size}!',
                                                    ephemeral=True)
            return

        guild = interaction.guild
        party_channel = await guild.fetch_channel(game_party.channel_id)
        player_user = await guild.fetch_member(game_player.player_id)
        existing_party = game.get_player_party(game_player)

        if existing_party is not None:
            existing_party_channel = await guild.fetch_channel(existing_party.channel_id)
            await existing_party_channel.set_permissions(player_user, read_messages=False, send_messages=False,
                                                         read_message_history=False)
            await existing_party_channel.send(f'**{game_player.player_discord_name}** has left {existing_party.party_name}!')
            existing_party.remove_player(game_player)

        game_party.add_player(game_player)

        await party_channel.set_permissions(player_user, read_messages=True, send_messages=True,
                                            read_message_history=True)

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'You have joined {game_party.party_name}!', ephemeral=True)
        await party_channel.send(f'**{game_player.player_discord_name}** has joined {game_party.party_name}!')

        mod_message = f'Player **{game_player.player_discord_name}** joined **{game_party.party_name}**'
        await modmsg(mod_message, guild)

    @app_commands.command(name="leave-party",
                          description="Allows a player to leave a party and manages text channel permissions")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    async def leave_party(self, interaction: discord.Interaction):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game_player = game.get_player(interaction.user.id)

        if not game.is_active:
            await interaction.response.send_message(
                f'The bot has been put in an inactive state by the moderator. Please try again later.', ephemeral=True)
            return
        elif game.parties_locked:
            await interaction.response.send_message(f'Parties are currently locked.', ephemeral=True)
            return

        if game_player is None:
            await interaction.response.send_message(f'You are not a registered player of the current game!')
            return
        if game_player.is_dead:
            await interaction.response.send_message(f'You are dead! Begone apparition!')
            return

        game_party = game.get_player_party(game_player)

        if game_party is None:
            await interaction.response.send_message(f'You are not currently a member of any party!')
            return

        guild = interaction.guild
        party_channel = await guild.fetch_channel(game_party.channel_id)
        player_user = await guild.fetch_member(game_player.player_id)

        game_party.remove_player(game_player)

        await party_channel.set_permissions(player_user, read_messages=False, send_messages=False,
                                            read_message_history=False)

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'You have left {game_party.party_name}!')
        await party_channel.send(f'**{game_player.player_discord_name}** has left {game_party.party_name}!')

        mod_message = f'Player **{game_player.player_discord_name}** left **{game_party.party_name}**'
        await modmsg(mod_message, guild)

async def setup(bot: commands.Bot) -> None:
    cog = PlayerManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')