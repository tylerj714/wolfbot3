#! command_autocompletes.py
# Utility class for managing autocomplete functionality

import discord
from discord import app_commands, Member, Guild, User
from typing import List, Optional, Literal, Dict
import bot.model.data_model as gdm
from bot.model.data_model import Game, Player, Round, Vote, Party, Dilemma
from bot.model.conf_vars import ConfVars as Conf
from bot.utils.string_decorator import emojify


async def player_list_autocomplete(interaction: discord.Interaction,
                                   current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)
    players = await get_valid_players(current, game.players)
    return [
        app_commands.Choice(name=player.player_discord_name, value=str(player.player_id))
        for player in players
    ]


async def get_valid_players(substr: str, players: List[Player]) -> List[Player]:
    player_list = []
    for player in sorted(players, key=lambda e: e.player_discord_name.lower()):
        if substr and substr.lower() not in player.player_discord_name.lower():
            continue
        if not player.is_dead:
            player_list.append(player)
    return player_list[:25]


async def party_list_autocomplete(interaction: discord.Interaction,
                                  current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)
    parties = await get_valid_parties(current, game.parties)
    return [
        app_commands.Choice(name=f'{party.party_name} ({len(party.player_ids)}/{party.max_size})',
                            value=str(party.channel_id))
        for party in parties
    ]


async def get_valid_parties(substr: str, parties: List[Party]) -> List[Party]:
    party_list = []
    for party in sorted(parties, key=lambda e: e.party_name.lower()):
        if substr and substr.lower() not in party.party_name.lower():
            continue
        party_list.append(party)
    return party_list[:25]


async def dilemma_name_autocomplete(interaction: discord.Interaction,
                                    current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)
    guild_member = await interaction.guild.fetch_member(interaction.user.id)
    dilemma_names = await get_valid_dilemma_names(current, game, guild_member)
    return [
        app_commands.Choice(name=dilemma_name, value=dilemma_name)
        for dilemma_name in dilemma_names
    ]


async def get_valid_dilemma_names(substr: str, game: Game, member: Member) -> List[str]:
    name_list = []
    dilemma_list = []
    game_round = game.get_latest_round()
    if game_round is not None:
        if member.guild_permissions.manage_guild:
            dilemma_list.extend(game_round.round_dilemmas)
        else:
            for round_dilemma in game_round.round_dilemmas:
                if member.id in round_dilemma.dilemma_player_ids:
                    dilemma_list.append(round_dilemma)
        for a_dilemma in dilemma_list:
            if substr and substr.lower() not in a_dilemma.dilemma_name.lower():
                continue
            name_list.append(a_dilemma.dilemma_name)
    return name_list[:25]


async def dilemma_choice_autocomplete(interaction: discord.Interaction,
                                      current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)
    dilemma_name = interaction.namespace.dilemma_name
    dilemma_choices = await get_valid_dilemma_choices(current, game, dilemma_name)
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in dilemma_choices
    ]


async def get_valid_dilemma_choices(substr: str, game: Game, dilemma_name: str) -> List[str]:
    choice_list = []
    game_round = game.get_latest_round()
    if game_round is not None:
        dilemma = game_round.get_dilemma(dilemma_name)
        for dilemma_choice in sorted(dilemma.dilemma_choices, key=lambda e: e.lower()):
            if substr and substr.lower() not in dilemma_choice.lower():
                continue
            choice_list.append(dilemma_choice)
    return choice_list[:25]


async def player_item_autocomplete(interaction: discord.Interaction,
                                   current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)
    player_id = interaction.namespace.player if interaction.namespace.player is not None else interaction.user.id
    game_player = game.get_player(player_id)
    item_choices = await get_player_item_choices(current, game_player)
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in item_choices
    ]


async def get_player_item_choices(substr: str, player: Player) -> List[str]:
    choice_list = []

    for item in sorted(player.player_items, key=lambda e: e.item_name.lower()):
        if substr and substr.lower() not in item.item_name.lower():
            continue
        choice_list.append(item.item_name)
    return choice_list[:25]


async def game_item_autocomplete(interaction: discord.Interaction,
                                 current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)
    item_choices = await get_game_item_choices(current, game)
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in item_choices
    ]


async def get_game_item_choices(substr: str, game: Game) -> List[str]:
    choice_list = []

    for item in sorted(game.items, key=lambda e: e.item_name.lower()):
        if substr and substr.lower() not in item.item_name.lower():
            continue
        choice_list.append(item.item_name)
    return choice_list[:25]


async def player_action_autocomplete(interaction: discord.Interaction,
                                     current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)
    player_id = interaction.namespace.player if interaction.namespace.player is not None else interaction.user.id
    game_player = game.get_player(player_id)
    action_choices = await get_player_action_choices(current, game_player)
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in action_choices
    ]


async def get_player_action_choices(substr: str, player: Player) -> List[str]:
    choice_list = []

    for action in sorted(player.player_actions, key=lambda e: e.action_name.lower()):
        if substr and substr.lower() not in action.action_name.lower():
            continue
        choice_list.append(action.action_name)

    # Also include item actions, where they are defined
    for item in sorted(player.player_items, key=lambda e: e.item_name.lower()):
        if item.item_action is not None:
            item_action = item.item_action
            if item_action.action_name is not None:
                if substr and substr.lower() not in item.item_name.lower():
                    continue
                choice_list.append(item_action.action_name)
    return choice_list[:25]


async def game_action_autocomplete(interaction: discord.Interaction,
                                   current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)

    action_choices = await get_game_action_choices(current, game)
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in action_choices
    ]


async def get_game_action_choices(substr: str, game: Game) -> List[str]:
    choice_list = []

    for action in sorted(game.actions, key=lambda e: e.action_name.lower()):
        if substr and substr.lower() not in action.action_name.lower():
            continue
        choice_list.append(action.action_name)

    return choice_list[:25]


async def attribute_type_autocomplete(interaction: discord.Interaction,
                                      current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)

    attribute_type_choices: list[str] = await get_attribute_type_names(current, game)
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in attribute_type_choices
    ]


async def get_attribute_type_names(substr: str, game: Game) -> list[str]:
    choice_list: list[str] = []

    for attribute_definition in sorted(game.attribute_definitions, key=lambda e: e.attribute_name.lower()):
        if substr and substr.lower() not in attribute_definition.attribute_name.lower():
            continue
        display_value = attribute_definition.attribute_name
        choice_list.append(display_value)

    return choice_list[:25]


async def resource_type_autocomplete(interaction: discord.Interaction,
                                     current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)

    resource_type_choices: list[str] = await get_resource_type_names(current, game)
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in resource_type_choices
    ]


async def get_resource_type_names(substr: str, game: Game) -> list[str]:
    choice_list: list[str] = []

    for resource_definition in sorted(game.resource_definitions, key=lambda e: e.resource_name.lower()):
        if substr and substr.lower() not in resource_definition.resource_name.lower():
            continue
        display_value = resource_definition.resource_name
        choice_list.append(display_value)

    return choice_list[:25]


async def persistent_view_autocomplete(interaction: discord.Interaction,
                                       current: str) -> List[app_commands.Choice[str]]:
    game = await gdm.get_game(file_path=Conf.GAME_PATH)

    view_choices = await get_persistent_view_names(current, game)
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in view_choices
    ]


async def get_persistent_view_names(substr: str, game: Game) -> List[str]:
    choice_list = []

    for pi_view in game.pi_views:
        if substr and substr.lower() not in pi_view.view_name.lower():
            continue
        choice_list.append(pi_view.view_name)

    return choice_list[:25]
