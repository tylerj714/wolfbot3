#! game_management.py
# Class with slash commands managing game state

import os
import discord
from discord import app_commands
from discord.ext import commands
from bot.model.conf_vars import ConfVars as Conf
from typing import Optional, Literal
import bot.model.data_model as gdm
from bot.model.data_model import Game, Action, Item, Player, Party, Round, Dilemma, Resource, ResourceCost, Attribute, \
    AttributeModifier, ResourceDefinition, AttributeDefinition, ItemTypeDefinition, Skill, StatusModifier
from bot.botlogger.logging_manager import log_interaction_call, log_info


class GameManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="initialize-game",
                          description="Creates a Game and saves the data to the defined json file")
    @app_commands.default_permissions(manage_guild=True)
    async def initialize_game(self,
                              interaction: discord.Interaction,
                              create_channels: Literal['True', 'False'],
                              party_prefix: Optional[str]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)

        if os.path.exists(Conf.GAME_PATH):
            await interaction.followup.send(f'Game file already exists! Delete the game file or change the '
                                            f'config to point to a new location or file!', ephemeral=True)
            return

        party_prefix = "" if not party_prefix else party_prefix

        generate_channels = True if create_channels == 'True' else False

        att_defs: list[AttributeDefinition] = await gdm.read_attribute_definitions_file(
            Conf.ATTRIBUTE_DEF_PATH) if Conf.ATTRIBUTE_DEF_PATH else []
        att_def_map: dict[str, AttributeDefinition] = gdm.map_attribute_definition_list(att_defs)
        res_defs: list[ResourceDefinition] = await gdm.read_resource_definitions_file(
            Conf.RESOURCE_DEF_PATH) if Conf.RESOURCE_DEF_PATH else []
        res_def_map: dict[str, ResourceDefinition] = gdm.map_resource_definition_list(res_defs)
        item_type_defs: list[ItemTypeDefinition] = await gdm.read_item_type_definitions_file(
            Conf.ITEM_TYPE_DEF_PATH) if Conf.ITEM_TYPE_DEF_PATH else []
        skills: list[Skill] = await gdm.read_skills_file(Conf.SKILL_PATH) if Conf.SKILL_PATH else []
        skill_map: dict[str, Skill] = gdm.map_skill_list(skills)
        status_mods: list[StatusModifier] = await gdm.read_status_modifiers_file(
            Conf.STATUS_MOD_PATH) if Conf.STATUS_MOD_PATH else []
        stat_mod_map: dict[str, StatusModifier] = gdm.map_status_modifier_list(status_mods)
        actions: list[Action] = await gdm.read_actions_file(Conf.ACTION_PATH) if Conf.ACTION_PATH else []
        action_map: dict[str, Action] = gdm.map_action_list(actions)
        items: list[Item] = await gdm.read_items_file(Conf.ITEM_PATH, game_actions=action_map) if Conf.ITEM_PATH else []
        item_map: dict[str, Item] = gdm.map_item_list(items)
        players: list[Player] = await gdm.read_players_file(Conf.PLAYER_PATH, game_actions=action_map,
                                                            game_items=item_map, game_resource_definitions=res_def_map,
                                                            game_attribute_definitions=att_def_map,
                                                            game_status_modifiers=stat_mod_map,
                                                            game_skills=skill_map
                                                            ) if Conf.PLAYER_PATH else []
        player_map: dict[int, Player] = gdm.map_player_list(players)
        parties: list[Party] = await gdm.read_parties_file(Conf.PARTY_PATH) if Conf.PARTY_PATH else []

        # If generate channels is enabled, generate channels for players and parties, if they are defined
        if generate_channels:
            category_channel = await interaction.guild.fetch_channel(Conf.MOD_CATEGORY)

            for player in players:
                discord_member = await interaction.guild.fetch_member(player.player_id)
                if player.player_mod_channel is None:
                    overwrites = {
                        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        discord_member: discord.PermissionOverwrite(read_messages=True, send_messages=False)
                    }

                    mod_channel_name = f'mod-{player.player_discord_name}'
                    mod_channel = await interaction.guild.create_text_channel(name=mod_channel_name,
                                                                              overwrites=overwrites,
                                                                              category=category_channel)
                    player.player_mod_channel = mod_channel.id

            private_chat_channel = await interaction.guild.fetch_channel(Conf.PRIVATE_CHAT_CATEGORY)
            for party in parties:
                if party.channel_id is None:
                    overwrites = {
                        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False)
                    }

                    party_channel_name = f'{party_prefix}{party.party_name}'
                    party_channel = await interaction.guild.create_text_channel(name=party_channel_name,
                                                                                overwrites=overwrites,
                                                                                category=private_chat_channel)
                    party.channel_id = party_channel.id
                else:
                    party_channel = await interaction.guild.fetch_channel(party.channel_id)

                for player_id in party.player_ids:
                    party_player = player_map[player_id]
                    party_member = await interaction.guild.fetch_member(player_id)
                    await party_channel.set_permissions(party_member, read_messages=True, send_messages=True,
                                                        read_message_history=True)
                    await party_channel.send(f'**{party_player.player_discord_name}** has joined {party.party_name}!')

        game = Game(is_active=False, parties_locked=True, voting_locked=True, items_locked=True, resources_locked=True,
                    players=players, parties=parties, rounds=[], attribute_definitions=att_defs,
                    resource_definitions=res_defs, item_type_definitions=item_type_defs, skills=skills,
                    status_modifiers=status_mods, actions=actions, items=items, pi_views=[])

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Initialized a new game at file location {Conf.GAME_PATH}')

    @app_commands.command(name="update-game-actions",
                          description="Updates the existing game with a new version of actions from the actions file")
    @app_commands.default_permissions(manage_guild=True)
    async def update_game_actions(self,
                                  interaction: discord.Interaction):
        log_interaction_call(interaction)

        game = gdm.read_json_to_dom(filepath=Conf.GAME_PATH)

        # TODO: Check if game exists, if it doesn't fail out

        actions = await gdm.read_actions_file(Conf.ACTION_PATH) if Conf.ACTION_PATH else []

        game.actions = actions

        # TODO: Iterate over players and also update their values (but not uses!)

        await gdm.write_game(game=game)

        await interaction.response.send_message(f'Updated game actions!')

    @app_commands.command(name="update-game-items",
                          description="Updates the existing game with a new version of items from the items file")
    @app_commands.default_permissions(manage_guild=True)
    async def update_game_items(self,
                                interaction: discord.Interaction):
        log_interaction_call(interaction)

        game = gdm.read_json_to_dom(filepath=Conf.GAME_PATH)

        # TODO: Check if game exists, if it doesn't fail out

        items = await gdm.read_items_file(Conf.ITEM_PATH) if Conf.ITEM_PATH else []

        game.items = items

        # TODO: Iterate over players and also update their values (but not uses!)

        await gdm.write_game(game=game)

        await interaction.response.send_message(f'Updated game items!')

    @app_commands.command(name="toggle-game-active-state",
                          description="Enables/Disables bot commands for players")
    @app_commands.default_permissions(manage_guild=True)
    async def toggle_game_active_state(self,
                                       interaction: discord.Interaction,
                                       is_active: Literal['True', 'False']):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game.is_active = True if is_active == 'True' else False

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'Game active state has been set to {is_active}!', ephemeral=True)

    @app_commands.command(name="party-toggle-lock-state",
                          description="Enables/Disables bot commands for Party functionality for players only")
    @app_commands.default_permissions(manage_guild=True)
    async def party_toggle_lock_state(self,
                                      interaction: discord.Interaction,
                                      is_locked: Literal['True', 'False']):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game.parties_locked = True if is_locked == 'True' else False

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'Player party lock status set to {is_locked}!', ephemeral=True)

    @app_commands.command(name="items-toggle-lock-state",
                          description="Enables/Disables bot commands for item functionality for players only")
    @app_commands.default_permissions(manage_guild=True)
    async def items_toggle_lock_state(self,
                                      interaction: discord.Interaction,
                                      is_locked: Literal['True', 'False']):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game.items_locked = True if is_locked == 'True' else False

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'Item transfer lock status set to {is_locked}!', ephemeral=True)

    @app_commands.command(name="voting-toggle-lock-state",
                          description="Enables/Disables bot commands for Voting functionality for players only")
    @app_commands.default_permissions(manage_guild=True)
    async def voting_toggle_lock_state(self,
                                       interaction: discord.Interaction,
                                       is_locked: Literal['True', 'False']):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game.voting_locked = True if is_locked == 'True' else False

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'Voting lock status set to {is_locked}!', ephemeral=True)

    @app_commands.command(name="resources-toggle-lock-state",
                          description="Enables/Disables bot commands for Resources functionality for players only")
    @app_commands.default_permissions(manage_guild=True)
    async def resources_toggle_lock_state(self,
                                          interaction: discord.Interaction,
                                          is_locked: Literal['True', 'False']):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game.resources_locked = True if is_locked == 'True' else False

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'Resources lock status set to {is_locked}!', ephemeral=True)

    @app_commands.command(name="clear-messages",
                          description="Clears up to 100 messages out of a discord channel")
    @app_commands.default_permissions(manage_guild=True)
    async def clear_messages(self,
                             interaction: discord.Interaction,
                             channel: discord.TextChannel,
                             channel_again: discord.TextChannel):
        log_interaction_call(interaction)

        if channel != channel_again:
            await interaction.response.send_message(
                f"Both channel arguments must be the same! This is a safety feature!")

        await interaction.response.send_message(f"Clearing messages from channel {channel.name}")
        await channel.purge(limit=100)

    @app_commands.command(name="delete-channels",
                          description="Deletes all channels in the chosen category")
    @app_commands.default_permissions(manage_guild=True)
    async def delete_channels(self,
                              interaction: discord.Interaction,
                              channel: discord.CategoryChannel,
                              channel_again: discord.CategoryChannel,
                              delete_category: Literal['True', 'False']):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)

        if channel != channel_again:
            await interaction.followup.send_message(
                f'Both channel arguments must be the same! This is a safety feature!', ephemeral=True)

        for sub_channel in channel.channels:
            await sub_channel.delete()

        if delete_category == 'True':
            await channel.delete()

        await interaction.followup.send(f'Deleted channels for category {channel.name}!', ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    cog = GameManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
