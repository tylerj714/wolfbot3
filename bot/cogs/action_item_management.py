#! action_item_management.py
# Class with slash commands managing actions and items

import discord
from discord import app_commands
from discord.ext import commands
from bot.model.conf_vars import ConfVars as Conf
import bot.model.data_model as gdm
from bot.botlogger.logging_manager import log_interaction_call, log_info
from bot.utils.command_autocompletes import game_item_autocomplete, player_item_autocomplete, player_list_autocomplete, \
    game_action_autocomplete, player_action_autocomplete
from bot.cogs.moderator_request_management import send_message_to_moderator as modmsg
from bot.utils.message_formatter import *


class ActionItemManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # @app_commands.command(name="items-handbook-view",
    #                       description="Displays an item from the spellbook")
    # @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    # @app_commands.autocomplete(item=game_item_autocomplete)
    # async def items_handbook_view(self,
    #                               interaction: discord.Interaction,
    #                               item: str):
    #     log_interaction_call(interaction)
    #     await interaction.response.defer(ephemeral=True, thinking=True)
    #     game = await gdm.get_game(file_path=Conf.GAME_PATH)
    #     guild = interaction.guild
    #
    #     item = game.get_item(item_name=item)
    #
    #     formatted_responses = await construct_item_display(items=[item], from_spellbook=True, guild=guild, game=game)
    #
    #     for responses in formatted_responses:
    #         await interaction.followup.send(f'{responses}', ephemeral=True)

    @app_commands.command(name="items-inventory-view",
                          description="Displays all current items in your inventory")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    async def items_inventory_view(self,
                                   interaction: discord.Interaction):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(interaction.user.id)
        sorted_player_items = sorted(game_player.player_items, key=lambda e: e.item_name.lower())

        formatted_responses = await construct_item_display(player=game_player, items=sorted_player_items,
                                                           guild=guild, game=game)

        for response in formatted_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="items-player-inventory-view",
                          description="Displays all current items in the chosen player's inventory")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    async def items_player_inventory_view(self,
                                          interaction: discord.Interaction,
                                          player: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))
        sorted_player_items = sorted(game_player.player_items, key=lambda e: e.item_name.lower())

        formatted_responses = await construct_item_display(player=game_player, items=sorted_player_items,
                                                           guild=guild, game=game)

        for response in formatted_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="items-send-to-player",
                          description="Allows a player to send an item to another player")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(item=player_item_autocomplete)
    async def items_send_to_player(self,
                                   interaction: discord.Interaction,
                                   item: str,
                                   player: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        if not game.is_active or game.items_locked:
            await interaction.response.send_message(
                f'The bot has been put in an inactive state by the moderator. Please try again later.', ephemeral=True)
            return
        elif game.items_locked:
            await interaction.response.send_message(f'Items cannot currently be sent!', ephemeral=True)
            return

        sending_player = game.get_player(interaction.user.id)
        receiving_player = game.get_player(int(player))

        item_to_send = sending_player.get_item(item)

        if item_to_send is None:
            await interaction.response.send_message(f'Item {item} not found in your inventory!', ephemeral=True)
        if receiving_player is None:
            await interaction.response.send_message(f'Recipient player was not a valid choice!', ephemeral=True)

        sending_player.remove_item(item_to_send)
        receiving_player.add_item(item_to_send)

        await gdm.write_game(game=game)

        await interaction.response.send_message(f'Sent item {item} to player {receiving_player.player_discord_name}!',
                                                ephemeral=True)

        sending_player_mod_channel = await interaction.guild.fetch_channel(
            sending_player.player_mod_channel) if sending_player.player_mod_channel is not None else None
        receiving_player_mod_channel = await interaction.guild.fetch_channel(
            receiving_player.player_mod_channel) if receiving_player.player_mod_channel is not None else None

        item_lost_formatted_responses = await construct_item_transfer_display(action='lost', item=item_to_send,
                                                                              guild=guild, game=game)
        item_gained_formatted_responses = await construct_item_transfer_display(action='gained', item=item_to_send,
                                                                                guild=guild, game=game)

        if sending_player_mod_channel is not None:
            for item_lost_response in item_lost_formatted_responses:
                await sending_player_mod_channel.send(f'{item_lost_response}')
        if receiving_player_mod_channel is not None:
            for item_gained_response in item_gained_formatted_responses:
                await receiving_player_mod_channel.send(f'{item_gained_response}')

        mod_message = f'Player **{sending_player.player_discord_name}** sent item **{item_to_send.item_name}** to **{receiving_player.player_discord_name}**'
        await modmsg(mod_message, guild)

    @app_commands.command(name="items-player-add",
                          description="Adds an item to a player's inventory from the game item config")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(item=game_item_autocomplete)
    async def items_player_add(self,
                               interaction: discord.Interaction,
                               player: str,
                               item: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))

        game_item = game.get_item(item)

        if game_item is None:
            await interaction.followup.send(f'Item {item} not defined in this game!', ephemeral=True)
        if game_player is None:
            await interaction.followup.send(f'Recipient player was not a valid choice!', ephemeral=True)

        game_player.add_item(game_item)
        item_mod_responses = await construct_item_transfer_display(action='gained', item=game_item, guild=guild,
                                                                   game=game)

        await gdm.write_game(game=game)

        await interaction.followup.send(
            f'Added item {item} to player {game_player.player_discord_name}\'s inventory!',
            ephemeral=True)

        player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None

        if player_mod_channel is not None:
            for response in item_mod_responses:
                await player_mod_channel.send(f'{response}')

    @app_commands.command(name="items-player-remove",
                          description="Removes an item from a player's inventory")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(item=player_item_autocomplete)
    async def items_player_remove(self,
                                  interaction: discord.Interaction,
                                  player: str,
                                  item: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))

        if game_player is None:
            await interaction.followup.send(f'Recipient player was not a valid choice!', ephemeral=True)
            return

        player_item = game_player.get_item(item)

        if player_item is None:
            await interaction.followup.send(f'Item {item} not defined in this game!', ephemeral=True)
            return

        game_player.remove_item(player_item)
        item_mod_responses = await construct_item_transfer_display(action='lost', item=player_item, guild=guild,
                                                                   game=game)

        await gdm.write_game(game=game)

        await interaction.followup.send(
            f'Remove item {item} from player {game_player.player_discord_name}\'s inventory!',
            ephemeral=True)

        player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None

        if player_mod_channel is not None:
            for response in item_mod_responses:
                await player_mod_channel.send(f'{response}')

    @app_commands.command(name="items-transfer-player",
                          description="Transfers an item from one player to another player")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(recipient_player=player_list_autocomplete)
    @app_commands.autocomplete(item=player_item_autocomplete)
    async def items_transfer_player(self,
                                    interaction: discord.Interaction,
                                    player: str,
                                    recipient_player: str,
                                    item: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        sending_player = game.get_player(int(player))
        receiving_player = game.get_player(int(recipient_player))

        item_to_send = sending_player.get_item(item)

        if item_to_send is None:
            await interaction.followup.send(
                f'Item {item} not found in the player {sending_player.player_discord_name}\'s inventory!',
                ephemeral=True)
        if receiving_player is None:
            await interaction.followup.send(f'Recipient player was not a valid choice!', ephemeral=True)

        sending_player.remove_item(item_to_send)
        receiving_player.add_item(item_to_send)

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Sent item {item} to player {receiving_player.player_discord_name}!',
                                        ephemeral=True)

        sending_player_mod_channel = await interaction.guild.fetch_channel(
            sending_player.player_mod_channel) if sending_player.player_mod_channel is not None else None
        receiving_player_mod_channel = await interaction.guild.fetch_channel(
            receiving_player.player_mod_channel) if receiving_player.player_mod_channel is not None else None

        item_lost_formatted_responses = await construct_item_transfer_display(action='lost', item=item_to_send,
                                                                              guild=guild, game=game)
        item_gained_formatted_responses = await construct_item_transfer_display(action='gained', item=item_to_send,
                                                                                guild=guild, game=game)

        if sending_player_mod_channel is not None:
            for item_lost_response in item_lost_formatted_responses:
                await sending_player_mod_channel.send(f'{item_lost_response}')
        if receiving_player_mod_channel is not None:
            for item_gained_response in item_gained_formatted_responses:
                await receiving_player_mod_channel.send(f'{item_gained_response}')

    # @app_commands.command(name="actions-handbook-view",
    #                       description="Displays a chosen action from the public spellbook")
    # @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    # @app_commands.autocomplete(action=game_action_autocomplete)
    # async def actions_handbook_view(self,
    #                                 interaction: discord.Interaction,
    #                                 action: str):
    #     log_interaction_call(interaction)
    #     await interaction.response.defer(ephemeral=True, thinking=True)
    #     game = await gdm.get_game(file_path=Conf.GAME_PATH)
    #     guild = interaction.guild
    #
    #     action = game.get_action(action_name=action)
    #
    #     formatted_responses = await construct_action_display(actions=[action], from_spellbook=True, guild=guild,
    #                                                          game=game)
    #
    #     for response in formatted_responses:
    #         await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="actions-available-view",
                          description="Displays all current actions you can use")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    async def actions_available_view(self,
                                     interaction: discord.Interaction):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(interaction.user.id)

        if game_player is None:
            await interaction.followup.send(f'You are not an active player of the current game!')
            return

        player_actions = game_player.player_actions
        player_item_actions: list[(str, Action)] = game_player.get_item_actions()
        item_action_names = [item_action_entry[1].action_name for item_action_entry in player_item_actions]
        non_item_player_actions = [action for action in player_actions if action.action_name not in item_action_names]
        sorted_player_item_actions = sorted(player_item_actions, key=lambda e: e[0].lower())
        sorted_non_item_player_actions = sorted(non_item_player_actions, key=lambda e: e.action_name.lower())

        formatted_responses = await construct_action_display(player=game_player,
                                                             actions=sorted_non_item_player_actions,
                                                             item_actions=sorted_player_item_actions,
                                                             guild=guild,
                                                             game=game)

        for response in formatted_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="actions-player-view",
                          description="Displays all current actions usable by the chosen player")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    async def actions_player_view(self,
                                  interaction: discord.Interaction,
                                  player: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))

        player_actions = game_player.player_actions
        player_item_actions: list[(str, Action)] = game_player.get_item_actions()
        item_action_names = [item_action_entry[1].action_name for item_action_entry in player_item_actions]
        non_item_player_actions = [action for action in player_actions if action.action_name not in item_action_names]
        sorted_player_item_actions = sorted(player_item_actions, key=lambda e: e[0].lower())
        sorted_non_item_player_actions = sorted(non_item_player_actions, key=lambda e: e.action_name.lower())

        formatted_responses = await construct_action_display(player=game_player,
                                                             actions=sorted_non_item_player_actions,
                                                             item_actions=sorted_player_item_actions,
                                                             guild=guild,
                                                             game=game)

        for response in formatted_responses:
            await interaction.followup.send(f'{response}', ephemeral=True)

    @app_commands.command(name="actions-player-add-uses",
                          description="Adds an action to the chosen player's action list")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(action=player_action_autocomplete)
    async def actions_player_add_uses(self,
                                      interaction: discord.Interaction,
                                      player: str,
                                      action: str,
                                      uses_to_add: app_commands.Range[int, 1, 5]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))
        player_action = game_player.get_action(action)

        if game_player is None:
            await interaction.followup.send(f'No valid player found with that identifier in the current game!')
            return
        if player_action is None:
            await interaction.followup.send(
                f'No action {action} could be found for the player {game_player.player_discord_name}!')
            return

        player_action.action_uses = player_action.action_uses + uses_to_add

        await gdm.write_game(game=game)

        formatted_responses = await construct_action_change_display(status='uses_increment', action=player_action,
                                                                    guild=guild,
                                                                    game=game, uses_changed=uses_to_add)

        player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None
        if player_mod_channel is not None:
            for response in formatted_responses:
                await player_mod_channel.send(f'{response}')

        await interaction.followup.send(
            f'Added {uses_to_add} uses to the action {action} of player {game_player.player_discord_name}!',
            ephemeral=True)

    @app_commands.command(name="actions-player-remove-uses",
                          description="Adds an action to the chosen player's action list")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(action=player_action_autocomplete)
    async def actions_player_remove_uses(self,
                                         interaction: discord.Interaction,
                                         player: str,
                                         action: str,
                                         uses_to_remove: app_commands.Range[int, 1, 5]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))
        player_action = game_player.get_action(action)

        if game_player is None:
            await interaction.followup.send(f'No valid player found with that identifier in the current game!')
            return
        if player_action is None:
            await interaction.followup.send(
                f'No action {action} could be found for the player {game_player.player_discord_name}!')
            return

        if player_action.action_uses <= uses_to_remove:
            player_action.action_uses = 0
        else:
            player_action.action_uses = player_action.action_uses - uses_to_remove

        await gdm.write_game(game=game)

        formatted_responses = await construct_action_change_display(status='uses_decrement', action=player_action,
                                                                    guild=guild,
                                                                    game=game, uses_changed=uses_to_remove)

        player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None
        if player_mod_channel is not None:
            for response in formatted_responses:
                await player_mod_channel.send(f'{response}')

        await interaction.followup.send(
            f'Removed {uses_to_remove} uses from the action {action} of player {game_player.player_discord_name}!',
            ephemeral=True)

    @app_commands.command(name="actions-player-add",
                          description="Adds an action to the chosen player's action list")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(action=game_action_autocomplete)
    async def actions_player_add(self,
                                 interaction: discord.Interaction,
                                 player: str,
                                 action: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        game_player = game.get_player(int(player))

        game_action = game.get_action(action)

        if game_player is None:
            await interaction.followup.send(f'No valid player found with that identifier in the current game!')
            return
        if game_action is None:
            await interaction.followup.send(f'No action {action} could be found in the current game!')
            return

        game_player.add_action(game_action)

        await gdm.write_game(game=game)

        formatted_responses = await construct_action_change_display(status='gained', action=game_action, guild=guild,
                                                                    game=game)

        player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None
        if player_mod_channel is not None:
            for response in formatted_responses:
                await player_mod_channel.send(f'{response}')

        await interaction.followup.send(
            f'Granted the action {action} to player {game_player.player_discord_name}!', ephemeral=True)

    @app_commands.command(name="actions-player-remove",
                          description="Removes an action from the chosen player's action list")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(action=player_action_autocomplete)
    async def actions_player_remove(self,
                                    interaction: discord.Interaction,
                                    player: str,
                                    action: str):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        game_player = game.get_player(int(player))

        if game_player is None:
            await interaction.followup.send(f'No valid player found with that identifier in the current game!')
            return

        player_action = game_player.get_action(action)

        if player_action is None:
            await interaction.followup.send(f'No action {action} could be found in the current game!')
            return

        game_player.remove_action(player_action)

        await gdm.write_game(game=game)

        formatted_responses = await construct_action_change_display(status='lost', action=player_action, guild=guild,
                                                                    game=game)

        player_mod_channel = await interaction.guild.fetch_channel(
            game_player.player_mod_channel) if game_player.player_mod_channel is not None else None
        if player_mod_channel is not None:
            for response in formatted_responses:
                await player_mod_channel.send(f'{response}')

        await interaction.followup.send(
            f'Removed the action {action} from player {game_player.player_discord_name}!', ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    cog = ActionItemManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
