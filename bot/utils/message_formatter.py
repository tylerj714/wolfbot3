import time
from typing import Optional, List, Literal
from discord import Guild
from bot.model.data_model import Player, Action, Item, Game, ResourceDefinition, ResourceCost, Resource, AttributeDefinition, \
    Attribute
import bot.utils.string_decorator as sdec

uses_to_emoji_map = {0: ":uses_zero:",
                     1: ":uses_one:",
                     2: ":uses_two:",
                     3: ":uses_three:",
                     4: ":uses_four:",
                     5: ":uses_five:"}


async def convert_uses_to_emoji(uses: int) -> str:
    if uses < 0:
        return ""

    if uses in uses_to_emoji_map:
        return uses_to_emoji_map[uses]
    else:
        return ":uses_five:+"


async def construct_action_display(guild: Guild, game: Game, player: Optional[Player] = None,
                                   actions: Optional[list[Action]] = None,
                                   item_actions: Optional[list[(str, Action)]] = None,
                                   from_spellbook: bool = False) -> list[str]:
    if actions is None:
        actions: list[Action] = []
    if item_actions is None:
        item_actions: list[(str, Action)] = []

    formatted_responses = []
    formatted_action_header = ""

    if from_spellbook:
        formatted_action_header += "Viewing Action Details..."
    elif player is not None:
        formatted_action_header += f'**Player {player.player_discord_name} Actions as of <t:{int(time.time())}>**\n'
    else:
        formatted_action_header += f'**Actions as of <t:{int(time.time())}>**\n'
    formatted_responses.append(await sdec.format_text(text=formatted_action_header, guild=guild))

    if actions is None and player is not None:
        actions = player.player_actions

    if item_actions is None and player is not None:
        item_actions = player.get_item_actions()

    if actions:
        formatted_actions = ""
        for action in actions:
            this_formatted_action = await format_action(action, game=game)
            if len(await sdec.format_text(text=formatted_actions, guild=guild)) + len(
                    await sdec.format_text(text=this_formatted_action, guild=guild)) <= 1750:
                formatted_actions += this_formatted_action
            else:
                formatted_responses.append(await sdec.format_text(text=formatted_actions, guild=guild))
                formatted_actions = ""
                formatted_actions += this_formatted_action
        formatted_responses.append(await sdec.format_text(text=formatted_actions, guild=guild))

    if item_actions:
        formatted_item_actions = ""
        for item_name, item_action in item_actions:
            this_formatted_item_action = await format_action(action=item_action, item_name=item_name, game=game)
            if len(await sdec.format_text(text=formatted_item_actions, guild=guild)) + len(
                    await sdec.format_text(text=this_formatted_item_action, guild=guild)) <= 1750:
                formatted_item_actions += this_formatted_item_action
            else:
                formatted_responses.append(await sdec.format_text(text=formatted_item_actions, guild=guild))
                formatted_item_actions = ""
                formatted_item_actions += this_formatted_item_action
        formatted_responses.append(await sdec.format_text(text=formatted_item_actions, guild=guild))

    if not actions and not item_actions:
        formatted_responses.append(await sdec.format_text(text=f'*<No Actions!>*', guild=guild))

    return formatted_responses


async def construct_action_change_display(guild: Guild,
                                          status: Literal['uses_increment', 'uses_decrement', 'gained', 'lost'],
                                          action: Action,
                                          game: Game,
                                          uses_changed: Optional[int] = 0) -> List[str]:
    formatted_responses = []
    formatted_action_change = ""

    if status == 'uses_increment':
        formatted_action_change += f'Your action **{action.action_name}** has gained {uses_changed} use(s)!\n'
        formatted_action_change += await format_action(action, game=game)
    elif status == 'uses_decrement':
        formatted_action_change += f'Yor action **{action.action_name}** has lost {uses_changed} use(s)!\n'
        formatted_action_change += await format_action(action, game=game)
    elif status == 'gained':
        formatted_action_change += f'You have been **granted** the action **{action.action_name}**:\n'
        formatted_action_change += await format_action(action, game=game)
    else:
        formatted_action_change += f'You have **lost** the action **{action.action_name}**!\n'

    formatted_responses.append(await sdec.format_text(text=formatted_action_change, guild=guild))

    return formatted_responses


async def format_action(action: Action, game: Game, item_name: Optional[str] = None) -> str:
    formatted_action = ""
    # TODO: Implement action classes
    # if action.action_classes and action.action_classes is not None:
    #     game_action_class_defs = game.get_action_class_definitions()
    #     for action_class in action.action_classes:
    #         if action_class.action_class_name in game_action_class_defs:
    #             action_class_def_str = game_action_class_defs[action_class.action_class_name].emoji_text
    #         else:
    #             action_class_def_str = action_class.action_class_name
    #         formatted_action += f' {action_class_def_str}'
    # Add action type display (following format_item pattern from lines 200-207)
    if action.action_type is not None:
        game_action_type_defs = game.get_action_type_definitions()
        if action.action_type in game_action_type_defs:
            action_type_def_str = game_action_type_defs[action.action_type].emoji_text
        else:
            action_type_def_str = action.action_type
        formatted_action += f' {action_type_def_str}'
    formatted_action += f' **{action.action_name}**:'
    if item_name:
        formatted_action += f' *(from {item_name})*'
    if action.action_timing:
        formatted_action += f' {action.action_timing} '
    if action.action_costs:
        formatted_action += f'- Cost: '
        costs = []
        for cost in action.action_costs:
            game_res_defs = game.get_resource_definitions()
            if cost.res_name in game_res_defs:
                res_def_display_name = game_res_defs[cost.res_name].emoji_text
            else:
                res_def_display_name = cost.res_name
            costs.append(f'{cost.amount} {res_def_display_name}')
        formatted_action += ' + '.join(costs) + " "
    if action.action_uses >= 0:
        uses_emoji = await convert_uses_to_emoji(action.action_uses)
        formatted_action += f'- {uses_emoji} '
    formatted_action += f'- {action.action_desc}'
    formatted_action += '\n'
    return formatted_action


async def construct_item_display(guild: Guild, game: Game, player: Optional[Player] = None,
                                 items: Optional[List[Item]] = None,
                                 from_spellbook: bool = False) -> List[str]:
    if items is None:
        items = []

    formatted_responses = []
    formatted_item_header = ""

    if from_spellbook:
        formatted_item_header += "Viewing Item Details..."
    elif player is not None:
        formatted_item_header += f'**Player {player.player_discord_name} Inventory as of <t:{int(time.time())}>**\n'
    else:
        formatted_item_header += f'**Inventory as of <t:{int(time.time())}>**\n'
    formatted_responses.append(await sdec.format_text(text=formatted_item_header, guild=guild))

    if items is None and player is not None:
        items = player.player_items

    if items:
        formatted_items = ""
        for item in items:
            this_formatted_item = await format_item(item, game=game)
            if len(await sdec.format_text(text=formatted_items, guild=guild)) + len(
                    await sdec.format_text(text=this_formatted_item, guild=guild)) <= 1750:
                formatted_items += this_formatted_item
            else:
                formatted_responses.append(await sdec.format_text(text=formatted_items, guild=guild))
                formatted_items = ""
                formatted_items += this_formatted_item
        formatted_responses.append(await sdec.format_text(text=formatted_items, guild=guild))
    else:
        formatted_responses.append(await sdec.format_text(text=f'*<No items!>*', guild=guild))

    return formatted_responses


async def construct_item_transfer_display(guild: Guild, action: Literal['gained', 'lost'], item: Item, game: Game) -> \
        List[str]:
    formatted_responses = []
    formatted_item = ""

    if action == 'gained':
        formatted_item += f'You have **gained possession** of the item **{item.item_name}**:\n'
        formatted_item += await format_item(item, game=game)
    else:
        formatted_item += f'You have **lost possession** of the item **{item.item_name}**!\n'

    formatted_responses.append(await sdec.format_text(text=formatted_item, guild=guild))

    return formatted_responses


async def format_item(item: Item, game: Game) -> str:
    formatted_item = f'-'
    if item.item_type is not None:
        game_item_type_defs = game.get_item_type_definitions()
        if item.item_type in game_item_type_defs:
            item_type_def_str = game_item_type_defs[item.item_type].emoji_text
        else:
            item_type_def_str = item.item_type
        formatted_item += f' {item_type_def_str}'
    formatted_item += f' **{item.item_name}**\n'
    if item.item_properties is not None:
        formatted_item += f' - {item.item_properties}\n'
    formatted_item += f'  - *{item.item_descr}*\n'
    if item.item_action is not None and item.item_action.action_name:
        item_action = item.item_action
        formatted_item += '\n'
        formatted_item += f'> - **{item_action.action_name}**: '
        if item_action.action_timing:
            formatted_item += f' {item_action.action_timing} '
        if item_action.action_costs:
            formatted_item += f'- Cost: '
            costs = []
            for cost in item_action.action_costs:
                game_res_defs = game.get_resource_definitions()
                if cost.res_name in game_res_defs:
                    res_def_display_name = game_res_defs[cost.res_name].emoji_text
                else:
                    res_def_display_name = cost.res_name
                costs.append(f'{cost.amount} {res_def_display_name}')
            formatted_item += ' + '.join(costs) + " "
        if item_action.action_uses and item_action.action_uses != -1:
            uses_emoji = await convert_uses_to_emoji(item_action.action_uses)
            formatted_item += f'- {uses_emoji} '
        formatted_item += f'- {item_action.action_desc}'
    formatted_item += '\n'
    return formatted_item


async def format_attribute(attribute_amt: int, attribute_definition: AttributeDefinition) -> str:
    if attribute_definition and attribute_definition.emoji_text:
        attribute_string = f"{attribute_amt} {attribute_definition.emoji_text} {attribute_definition.attribute_name}"
    else:
        attribute_string = f"{attribute_amt} {attribute_definition.attribute_name}"
    return attribute_string


async def construct_attribute_modified_display(guild: Guild, action: Literal['increased', 'decreased'],
                                               player_attribute: Attribute, att_change_amt: int, game: Game) -> List[str]:
    formatted_responses = []
    formatted_attribute = ""

    attribute_definition: AttributeDefinition = game.get_attribute_definition_by_name(player_attribute.name)
    attribute_string = await format_attribute(attribute_amt=player_attribute.level,
                                              attribute_definition=attribute_definition)
    change_att_str = await format_attribute(attribute_amt=att_change_amt, attribute_definition=attribute_definition)

    if action == 'increased':
        formatted_attribute += f'You have **gained** {change_att_str}!\n'
    elif action == 'decreased':
        formatted_attribute += f'You have **lost** {change_att_str}\n'
    formatted_attribute += f'You now have {attribute_string}'

    formatted_responses.append(await sdec.format_text(text=formatted_attribute, guild=guild))

    return formatted_responses


async def construct_player_attributes_display(player: Player, guild: Guild, game: Game) -> List[str]:
    formatted_responses = []

    formatted_attributes = ""

    formatted_player_attribute_header = f'**Player {player.player_discord_name} Attributes as of <t:{int(time.time())}>**\n'
    formatted_responses.append(formatted_player_attribute_header)

    for player_attribute in player.player_attributes:
        att_def: AttributeDefinition = game.get_attribute_definition_by_name(player_attribute.name)

        this_formatted_attribute = await format_attribute(attribute_amt=player_attribute.level,
                                                          attribute_definition=att_def) + "\n"
        if len(await sdec.format_text(text=formatted_attributes, guild=guild)) + len(
                await sdec.format_text(text=this_formatted_attribute, guild=guild)) <= 1750:
            formatted_attributes += this_formatted_attribute
        else:
            formatted_responses.append(await sdec.format_text(text=formatted_attributes, guild=guild))
            formatted_attributes = ""
            formatted_attributes += this_formatted_attribute
    if formatted_attributes:
        formatted_responses.append(await sdec.format_text(text=formatted_attributes, guild=guild))

    return formatted_responses


async def format_attribute_row(attribute_defs: dict[str, AttributeDefinition], player: Player) -> str:

    attribute_substrs = []
    player_name = (player.player_discord_name[:23] + '..') if len(player.player_discord_name) > 25 else '{:25}'.format(player.player_discord_name)
    attribute_substrs.append(f"{player_name}")

    for attribute in player.player_attributes:
        attribute_def = attribute_defs.get(attribute.name, None)

        att_lvl = attribute.level
        att_emoji = attribute_def.emoji_text if attribute_def else ""
        att_name = attribute_def.attribute_name if attribute_def else attribute.name

        if att_emoji:
            attribute_substrs.append(f"{att_lvl} {att_emoji} {att_name}")
        else:
            attribute_substrs.append(f"{att_lvl} {att_name}")

    attribute_string = ' | '.join(attribute_substrs) + "\n"

    return attribute_string


async def construct_player_attributes_display_table(players: List[Player], guild: Guild, game: Game) -> List[str]:
    formatted_responses = []

    formatted_attributes = ""

    formatted_player_attribute_header = f'**Aggregate Player Attributes as of <t:{int(time.time())}>**\n'
    formatted_responses.append(formatted_player_attribute_header)

    att_defs: dict[str, AttributeDefinition] = game.get_attribute_definitions()

    for player in players:
        formatted_attribute_row = await format_attribute_row(attribute_defs=att_defs, player=player)

        if len(await sdec.format_text(text=formatted_attributes, guild=guild)) + len(
                await sdec.format_text(text=formatted_attribute_row, guild=guild)) <= 1500:
            formatted_attributes += formatted_attribute_row
        else:
            formatted_responses.append(await sdec.format_text(text=formatted_attributes, guild=guild))
            formatted_attributes = ""
            formatted_attributes += formatted_attribute_row
    if formatted_attributes:
        formatted_responses.append(await sdec.format_text(text=formatted_attributes, guild=guild))

    return formatted_responses


async def format_resource(resource_amt: int, resource_definition: ResourceDefinition) -> str:
    if resource_definition and resource_definition.emoji_text:
        resource_string = f"{resource_amt} {resource_definition.emoji_text} {resource_definition.resource_name}"
    else:
        resource_string = f"{resource_amt} {resource_definition.resource_name}"
    return resource_string


async def construct_resource_modified_display(guild: Guild, action: Literal[
    'gained', 'lost', 'income', 'expired', 'received', 'sent'],
                                              player_resource: Resource, res_change_amt: int, game: Game) -> List[str]:
    formatted_responses = []
    formatted_resource = ""

    resource_definition: ResourceDefinition = game.get_resource_definition_by_name(player_resource.resource_type)
    resource_string = await format_resource(resource_amt=player_resource.resource_amt,
                                            resource_definition=resource_definition)
    change_res_str = await format_resource(resource_amt=res_change_amt, resource_definition=resource_definition)

    if action == 'income' or action == 'expired':
        if action == 'income':
            formatted_resource += f'You have **gained** {change_res_str} from daily income!\n'
        elif action == 'expired':
            formatted_resource += f'You have **lost** {change_res_str} due to resource expiration!\n'
    else:
        if action == 'gained':
            formatted_resource += f'You have **gained** {change_res_str}\n'
        elif action == 'lost':
            formatted_resource += f'You have **lost** {change_res_str}\n'
        elif action == 'received':
            formatted_resource += f'You have **received** {change_res_str}\n'
        else:
            formatted_resource += f'You have **sent** {change_res_str}\n'
        formatted_resource += f'You now have {resource_string}'

    formatted_responses.append(await sdec.format_text(text=formatted_resource, guild=guild))

    return formatted_responses


async def construct_player_resources_display(player: Player, guild: Guild, game: Game) -> List[str]:
    formatted_responses = []

    formatted_action_header = f'**Player {player.player_discord_name} Resources as of <t:{int(time.time())}>**\n'
    formatted_responses.append(formatted_action_header)

    formatted_resources = ""
    for player_resource in player.player_resources:
        res_def: ResourceDefinition = game.get_resource_definition_by_name(player_resource.resource_type)

        this_formatted_resource = await format_resource(resource_amt=player_resource.resource_amt,
                                                        resource_definition=res_def) + "\n"
        if len(await sdec.format_text(text=formatted_resources, guild=guild)) + len(
                await sdec.format_text(text=this_formatted_resource, guild=guild)) <= 1750:
            formatted_resources += this_formatted_resource
        else:
            formatted_responses.append(await sdec.format_text(text=formatted_resources, guild=guild))
            formatted_resource = ""
            formatted_resource += this_formatted_resource
    if formatted_resources:
        formatted_responses.append(await sdec.format_text(text=formatted_resources, guild=guild))

    return formatted_responses


async def format_resource_row(resource_defs: dict[str, ResourceDefinition], player: Player) -> str:

    resource_substrs = []
    player_name = (player.player_discord_name[:23] + '..') if len(player.player_discord_name) > 25 else '{:25}'.format(player.player_discord_name)
    resource_substrs.append(f"{player_name}")

    for resource in player.player_resources:
        resource_def = resource_defs.get(resource.resource_type, None)

        att_lvl = resource.resource_amt
        att_emoji = resource_def.emoji_text if resource_def else ""
        att_name = resource_def.resource_name if resource_def else resource.resource_type

        if att_emoji:
            resource_substrs.append(f"{att_lvl} {att_emoji} {att_name}")
        else:
            resource_substrs.append(f"{att_lvl} {att_name}")

    resource_string = ' | '.join(resource_substrs) + "\n"

    return resource_string


async def construct_player_resources_display_table(players: List[Player], guild: Guild, game: Game) -> List[str]:
    formatted_responses = []

    formatted_resources = ""

    formatted_player_resource_header = f'**Aggregate Player Resources as of <t:{int(time.time())}>**\n'
    formatted_responses.append(formatted_player_resource_header)

    res_defs: dict[str, ResourceDefinition] = game.get_resource_definitions()

    for player in players:
        formatted_resource_row = await format_resource_row(resource_defs=res_defs, player=player)

        if len(await sdec.format_text(text=formatted_resources, guild=guild)) + len(
                await sdec.format_text(text=formatted_resource_row, guild=guild)) <= 1500:
            formatted_resources += formatted_resource_row
        else:
            formatted_responses.append(await sdec.format_text(text=formatted_resources, guild=guild))
            formatted_resources = ""
            formatted_resources += formatted_resource_row
    if formatted_resources:
        formatted_responses.append(await sdec.format_text(text=formatted_resources, guild=guild))

    return formatted_responses


async def insufficient_resources_msg(action: Action, player: Player, game: Game, guild: Guild) -> list[str]:
    formatted_responses = []

    formatted_action_header = f'**Insufficient resources for action {action.action_name}!\n'
    formatted_responses.append(formatted_action_header)

    formatted_resources = ""
    for resource_cost in action.action_costs:
        player_resource = player.get_resource(resource_cost.res_name)
        res_def: ResourceDefinition = game.get_resource_definition_by_name(player_resource.resource_type)

        this_formatted_resource_cost = await format_resource(resource_amt=resource_cost.amount,
                                                             resource_definition=res_def)
        if player_resource:
            this_formatted_player_resource = await format_resource(resource_amt=player_resource.resource_amt,
                                                                   resource_definition=res_def)
        else:
            this_formatted_player_resource = await format_resource(resource_amt=0, resource_definition=res_def)

        this_formatted_resource = f"Action Resource Cost: {this_formatted_resource_cost}; " \
                                  f"Player Resources: {this_formatted_player_resource}\n"

        if len(await sdec.format_text(text=formatted_resources, guild=guild)) + len(
                await sdec.format_text(text=this_formatted_resource, guild=guild)) <= 1750:
            formatted_resources += this_formatted_resource
        else:
            formatted_responses.append(await sdec.format_text(text=formatted_resources, guild=guild))
            formatted_resource = ""
            formatted_resource += this_formatted_resource
    formatted_responses.append(await sdec.format_text(text=formatted_resources, guild=guild))

    return formatted_responses
