#! game_manager.py
# a class for managing game state details
import json
import traceback
from typing import Optional, List, Dict, Set
from bot.botlogger.logging_manager import logger
import csv
import time
import os
from bot.model.conf_vars import ConfVars as Conf


class PersistentInteractableView:
    def __init__(self, view_name: str, channel_id: int, message_ids: list[int], button_msg_id: int):
        self.view_name = view_name
        self.channel_id = channel_id
        self.message_ids = message_ids
        self.button_msg_id = button_msg_id


class AttributeModifier:
    def __init__(self, att_name: str, modification: int):
        self.att_name = att_name
        self.modification = modification


class Attribute:
    def __init__(self, name: str, level: int, max_level: int):
        self.name = name
        self.level = level
        self.max_level = max_level


class ResourceCost:
    def __init__(self, res_name: str, amount: int):
        self.res_name = res_name
        self.amount = amount


class Resource:
    def __init__(self, resource_type: str, resource_amt: int, resource_income: int, resource_max: int,
                 is_commodity: bool, is_perishable):
        self.resource_type = resource_type
        self.resource_amt = resource_amt
        self.resource_income = resource_income
        self.resource_max = resource_max
        self.is_commodity = is_commodity
        self.is_perishable = is_perishable


class Skill:
    def __init__(self, skill_name: str, skill_req: str, skill_restrict: str, skill_desc: str,
                 modifies_attributes: List[AttributeModifier]):
        self.skill_name = skill_name
        self.skill_req = skill_req
        self.skill_restrict = skill_restrict
        self.skill_desc = skill_desc
        self.modifies_attributes = modifies_attributes


class StatusModifier:
    def __init__(self, modifier_type: str, modifier_name: str, modifier_desc: str, modifier_duration: int,
                 modifier_stacks: int,
                 modifies_attributes: List[AttributeModifier]):
        self.modifier_type = modifier_type
        self.modifier_name = modifier_name
        self.modifier_desc = modifier_desc
        self.modifier_duration = modifier_duration
        self.modifier_stacks = modifier_stacks
        self.modifies_attributes = modifies_attributes


class Action:
    def __init__(self, action_name: str, action_timing: str, action_costs: List[ResourceCost], action_uses: int,
                 action_classes: [str], action_level_req: int, action_priority: int, action_desc: str):
        self.action_name = action_name
        self.action_timing = action_timing
        self.action_costs = action_costs
        self.action_uses = action_uses
        self.action_classes = action_classes
        self.action_level_req = action_level_req
        self.action_priority = action_priority
        self.action_desc = action_desc


class Item:
    def __init__(self, item_name: str, item_type: str, item_subtype: str, item_rarity: str, item_properties: str,
                 item_desc: str, is_equipped: bool, item_action: Optional[Action]):
        self.item_name = item_name
        self.item_type = item_type
        self.item_subtype = item_subtype
        self.item_rarity = item_rarity
        self.item_properties = item_properties
        self.item_descr = item_desc
        self.is_equipped = is_equipped
        self.item_action = item_action


class Player:
    def __init__(self, player_id: int, player_discord_name: str, player_mod_channel: int,
                 player_resources: List[Resource], player_attributes: List[Attribute],
                 player_status_mods: List[StatusModifier], player_skills: List[Skill],
                 player_actions: List[Action], player_items: List[Item],
                 is_dead: bool = False):
        self.player_id = player_id
        self.player_discord_name = player_discord_name
        self.player_mod_channel = player_mod_channel
        self.player_resources = player_resources
        self.player_attributes = player_attributes
        self.player_status_mods = player_status_mods
        self.player_skills = player_skills
        self.player_actions = player_actions
        self.player_items = player_items
        self.is_dead = is_dead

    def get_action(self, action_name: str) -> Optional[Action]:
        specific_action: Optional[Action] = None
        for action in self.player_actions:
            if action.action_name == action_name:
                specific_action = action
        for item in self.player_items:
            if item.item_action is not None:
                if item.item_action.action_name == action_name:
                    specific_action = item.item_action
        return specific_action

    def add_action(self, action: Action):
        self.player_actions.append(action)

    def remove_action(self, action: Action):
        self.player_actions.remove(action)

    def get_item(self, item_name: str) -> Optional[Item]:
        specific_item: Optional[Item] = None
        for item in self.player_items:
            if item.item_name == item_name:
                specific_item = item
        return specific_item

    def add_item(self, item: Item):
        self.player_items.append(item)

    def remove_item(self, item: Item):
        self.player_items.remove(item)

    def get_item_actions(self) -> list[(str, Action)]:
        item_actions: list[(str, Action)] = []
        for item in self.player_items:
            if item.item_action is not None:
                item_tuple = (item.item_name, item.item_action)
                item_actions.append(item_tuple)
        return item_actions

    def get_resource(self, resource_name: str) -> Optional[Resource]:
        for resource in self.player_resources:
            if resource.resource_type == resource_name:
                return resource
        return None

    def modify_resource(self, resource_name: str, amt: int):
        resource_to_modify = self.get_resource(resource_name=resource_name)
        if resource_to_modify:
            if resource_to_modify.resource_max != -1 and resource_to_modify.resource_amt + amt >= resource_to_modify.resource_max:
                resource_to_modify.resource_amt = resource_to_modify.resource_max
            elif resource_to_modify.resource_amt + amt <= 0:
                resource_to_modify.resource_amt = 0
            else:
                resource_to_modify.resource_amt = resource_to_modify.resource_amt + amt
        else:
            logger.warn(f"Attempted to add resource {resource_name} to player, but player does not have this resource!")

    def get_attribute(self, attribute_name: str) -> Optional[Attribute]:
        for attribute in self.player_attributes:
            if attribute.name == attribute_name:
                return attribute
        return None

    def modify_attribute(self, attribute_name: str, amt: int):
        attribute_to_modify = self.get_attribute(attribute_name=attribute_name)
        if attribute_to_modify:
            if attribute_to_modify.max_level != -1 and attribute_to_modify.level + amt >= attribute_to_modify.max_level:
                attribute_to_modify.level = attribute_to_modify.max_level
            elif attribute_to_modify.level + amt <= 0:
                attribute_to_modify.level = 0
            else:
                attribute_to_modify.level = attribute_to_modify.level + amt
        else:
            logger.warn(f"Attempted to modify {attribute_name} of player, but player does not have this attribute!")


class Vote:
    def __init__(self, player_id: int, choice: str, timestamp: int):
        self.player_id = player_id
        self.choice = choice
        self.timestamp = timestamp


class Dilemma:
    def __init__(self, dilemma_votes: List[Vote], dilemma_name: str, dilemma_channel_id: int, dilemma_message_id: int,
                 dilemma_player_ids: Set[int], dilemma_choices: Set[str], is_active_dilemma: bool):
        self.dilemma_votes = dilemma_votes
        self.dilemma_name = dilemma_name
        self.dilemma_channel_id = dilemma_channel_id
        self.dilemma_message_id = dilemma_message_id
        self.dilemma_player_ids = dilemma_player_ids
        self.dilemma_choices = dilemma_choices
        self.is_active_dilemma = is_active_dilemma

    def get_player_vote(self, player_id: int) -> Optional[Vote]:
        player_vote = None
        for vote in self.dilemma_votes:
            if vote.player_id == player_id:
                player_vote = vote
        return player_vote

    def add_vote(self, vote: Vote):
        self.dilemma_votes.append(vote)

    def remove_vote(self, vote: Vote):
        self.dilemma_votes.remove(vote)

    def add_player(self, player: Player):
        self.dilemma_player_ids.add(player.player_id)

    def remove_player(self, player: Player):
        self.dilemma_player_ids.remove(player.player_id)

    def add_choice(self, choice: str):
        self.dilemma_choices.add(choice)

    def remove_choice(self, choice: str):
        self.dilemma_choices.remove(choice)


class Party:
    def __init__(self, player_ids: Set[int], party_name: str, max_size: int, channel_id: int):
        self.player_ids = player_ids
        self.channel_id = channel_id
        self.party_name = party_name
        self.max_size = max_size

    def add_player(self, player: Player):
        self.player_ids.add(player.player_id)

    def remove_player(self, player: Player):
        self.player_ids.remove(player.player_id)


class Round:
    def __init__(self, votes: List[Vote], round_channel_id: int, round_message_id: int, round_number: int,
                 round_dilemmas: List[Dilemma], is_active_round: bool):
        self.votes = votes
        self.round_channel_id = round_channel_id
        self.round_message_id = round_message_id
        self.round_dilemmas = round_dilemmas
        self.round_number = round_number
        self.is_active_round = is_active_round

    def add_dilemma(self, dilemma: Dilemma):
        self.round_dilemmas.append(dilemma)

    def close_dilemmas(self):
        for dilemma in self.round_dilemmas:
            dilemma.is_active_dilemma = False

    def get_dilemmas(self):
        return self.round_dilemmas

    def get_dilemma(self, dilemma_name) -> Optional[Dilemma]:
        player_dilemma = None
        for a_dilemma in self.round_dilemmas:
            if dilemma_name == a_dilemma.dilemma_name:
                player_dilemma = a_dilemma
        return player_dilemma

    def get_player_vote(self, player_id: int) -> Optional[Vote]:
        player_vote = None
        for vote in self.votes:
            if vote.player_id == player_id:
                player_vote = vote
        return player_vote

    def add_vote(self, vote: Vote):
        self.votes.append(vote)

    def remove_vote(self, vote: Vote):
        self.votes.remove(vote)


class AttributeDefinition:
    def __init__(self, attribute_name: str, attribute_max: int, emoji_text: str):
        self.attribute_name = attribute_name
        self.attribute_max = attribute_max
        self.emoji_text = emoji_text


class ResourceDefinition:
    def __init__(self, resource_name: str, resource_max: int, is_commodity: bool, is_perishable: bool, emoji_text: str):
        self.resource_name = resource_name
        self.resource_max = resource_max
        self.is_commodity = is_commodity
        self.is_perishable = is_perishable
        self.emoji_text = emoji_text


class ItemTypeDefinition:
    def __init__(self, item_type: str, is_equippable: bool, max_equippable: int, emoji_text: str):
        self.item_type = item_type
        self.is_equippable = is_equippable
        self.max_equippable = max_equippable
        self.emoji_text = emoji_text


class Game:
    def __init__(self, is_active: bool, parties_locked: bool, voting_locked: bool, items_locked: bool,
                 resources_locked: bool, players: List[Player], parties: List[Party], rounds: List[Round],
                 attribute_definitions: List[AttributeDefinition], resource_definitions: List[ResourceDefinition],
                 item_type_definitions: List[ItemTypeDefinition], skills: List[Skill],
                 status_modifiers: List[StatusModifier], actions: List[Action], items: List[Item],
                 pi_views: List[PersistentInteractableView]):
        self.is_active = is_active
        self.parties_locked = parties_locked
        self.voting_locked = voting_locked
        self.items_locked = items_locked
        self.resources_locked = resources_locked
        self.players = players
        self.rounds = rounds
        self.parties = parties
        self.attribute_definitions = attribute_definitions
        self.resource_definitions = resource_definitions
        self.item_type_definitions = item_type_definitions
        self.skills = skills
        self.status_modifiers = status_modifiers
        self.actions = actions
        self.items = items
        self.pi_views = pi_views

    def get_player(self, player_id: int | str) -> Optional[Player]:
        player_int_id = player_id if isinstance(player_id, int) else int(player_id)
        for player in self.players:
            if player.player_id == player_int_id:
                return player
        return None

    def add_player(self, player: Player):
        self.players.append(player)

    def get_living_player_ids(self) -> List[str]:
        game_player_ids = []
        for player in self.players:
            game_player_ids.append(str(player.player_id))
        return game_player_ids

    def add_round(self, a_round: Round):
        self.rounds.append(a_round)

    def get_round(self, round_num: int) -> Optional[Round]:
        for a_round in self.rounds:
            if a_round.round_number == round_num:
                return a_round
        return None

    def get_latest_round(self) -> Optional[Round]:
        latest_round = None
        previous_round_num = 0
        for a_round in self.rounds:
            if a_round.round_number > previous_round_num:
                previous_round_num = a_round.round_number
                latest_round = a_round
        return latest_round

    def add_party(self, a_party: Party):
        self.parties.append(a_party)

    def get_party(self, channel_id: int):
        for a_party in self.parties:
            if a_party.channel_id == channel_id:
                return a_party
        return None

    def get_player_party(self, player: Player):
        for a_party in self.parties:
            if player.player_id in a_party.player_ids:
                return a_party
        return None

    def get_action(self, action_name: str) -> Optional[Action]:
        for action in self.actions:
            if action.action_name == action_name:
                return action
        return None

    def get_action_map(self) -> Dict[str, Action]:
        action_dict: Dict[str, Action] = {}
        for action in self.actions:
            action_dict[action.action_name] = action
        return action_dict

    def get_item(self, item_name: str) -> Optional[Item]:
        for item in self.items:
            if item.item_name == item_name:
                return item
        return None

    def get_item_map(self) -> Dict[str, Item]:
        item_dict: Dict[str, Item] = {}
        for item in self.items:
            item_dict[item.item_name] = item
        return item_dict

    def get_item_actions(self) -> list[(str, Action)]:
        item_actions: list[(str, Action)] = []
        for item in self.items:
            if item.item_action is not None:
                item_tuple = (item.item_name, item.item_action)
                item_actions.append(item_tuple)
        return item_actions

    def get_item_type_definitions(self) -> Dict[str, ItemTypeDefinition]:
        item_type_def_dict: Dict[str, ItemTypeDefinition] = {}
        for item_type_def in self.item_type_definitions:
            item_type_def_dict[item_type_def.item_type] = item_type_def
        return item_type_def_dict

    def get_attribute_definitions(self) -> Dict[str, AttributeDefinition]:
        att_def_dict: Dict[str, AttributeDefinition] = {}
        for att_def in self.attribute_definitions:
            att_def_dict[att_def.attribute_name] = att_def
        return att_def_dict

    def get_attribute_definition_by_name(self, attribute_name: str) -> Optional[AttributeDefinition]:
        for att_def in self.attribute_definitions:
            if att_def.attribute_name == attribute_name:
                return att_def
        return None

    def get_resource_definitions(self) -> Dict[str, ResourceDefinition]:
        res_def_dict: Dict[str, ResourceDefinition] = {}
        for res_def in self.resource_definitions:
            res_def_dict[res_def.resource_name] = res_def
        return res_def_dict

    def get_resource_definition_by_name(self, resource_name: str) -> Optional[ResourceDefinition]:
        for res_def in self.resource_definitions:
            if res_def.resource_name == resource_name:
                return res_def
        return None

    def get_pi_view(self, view_name: str) -> Optional[PersistentInteractableView]:
        for pi_view in self.pi_views:
            if pi_view.view_name == view_name:
                return pi_view
        return None

    def remove_pi_view(self, view_name: str):
        for pi_view in self.pi_views:
            if pi_view.view_name == view_name:
                self.pi_views.remove(pi_view)


def map_player_list(players: List[Player]) -> Dict[int, Player]:
    player_dict: Dict[int, Player] = {}
    for player in players:
        player_dict[player.player_id] = player
    return player_dict

def map_status_modifier_list(stat_mods: List[StatusModifier]) -> Dict[str, StatusModifier]:
    stat_mod_dict: Dict[str, StatusModifier] = {}
    for stat_mod in stat_mods:
        stat_mod_dict[stat_mod.modifier_name] = stat_mod
    return stat_mod_dict

def map_skill_list(skills: List[Skill]) -> Dict[str, Skill]:
    skill_dict: Dict[str, Skill] = {}
    for skill in skills:
        skill_dict[skill.skill_name] = skill
    return skill_dict

def map_resource_definition_list(res_defs: List[ResourceDefinition]) -> Dict[str, ResourceDefinition]:
    res_def_dict: Dict[str, ResourceDefinition] = {}
    for res_def in res_defs:
        res_def_dict[res_def.resource_name] = res_def
    return res_def_dict

def map_attribute_definition_list(att_defs: List[AttributeDefinition]) -> Dict[str, AttributeDefinition]:
    att_def_dict: Dict[str, AttributeDefinition] = {}
    for att_def in att_defs:
        att_def_dict[att_def.attribute_name] = att_def
    return att_def_dict

def map_action_list(actions: List[Action]) -> Dict[str, Action]:
    action_dict: Dict[str, Action] = {}
    for action in actions:
        action_dict[action.action_name] = action
    return action_dict


def map_item_list(items: List[Item]) -> Dict[str, Item]:
    item_dict: Dict[str, Item] = {}
    for item in items:
        item_dict[item.item_name] = item
    return item_dict


def read_json_to_dom(filepath: str) -> Game:
    try:
        with open(filepath, 'r', encoding="utf8") as openfile:
            json_object = json.load(openfile)

            is_active = json_object.get("is_active")
            parties_locked = json_object.get("parties_locked")
            voting_locked = json_object.get("voting_locked")
            items_locked = json_object.get("items_locked")
            resources_locked = json_object.get("resources_locked")
            players = []
            rounds = []
            parties = []
            attribute_defs = []
            if dict_val_ne(json_object, 'attribute_defs'):
                for attribute_def_entry in json_object.get("attribute_defs"):
                    attribute_name = attribute_def_entry.get("attribute_name")
                    attribute_max = int_w_default(
                        attribute_def_entry.get("attribute_max"), -1) if dict_val_ne(attribute_def_entry,
                                                                                     'attribute_max') else -1
                    att_emoji_text = attribute_def_entry.get("emoji_text")
                    attribute_defs.append(AttributeDefinition(attribute_name=attribute_name,
                                                              attribute_max=attribute_max,
                                                              emoji_text=att_emoji_text))
            resource_defs = []
            if dict_val_ne(json_object, 'resource_defs'):
                for resource_def_entry in json_object.get("resource_defs"):
                    resource_name = resource_def_entry.get("resource_name")
                    resource_max = int_w_default(
                        resource_def_entry.get("resource_max"), -1) if dict_val_ne(resource_def_entry,
                                                                                   'resource_max') else -1
                    is_commodity = resource_def_entry.get("is_commodity")
                    is_perishable = resource_def_entry.get("is_perishable")
                    res_emoji_text = resource_def_entry.get("emoji_text")
                    resource_defs.append(ResourceDefinition(resource_name=resource_name,
                                                            resource_max=resource_max,
                                                            is_commodity=is_commodity,
                                                            is_perishable=is_perishable,
                                                            emoji_text=res_emoji_text))
            item_type_defs = []
            if dict_val_ne(json_object, 'item_type_defs'):
                for item_type_def_entry in json_object.get("item_type_defs"):
                    item_type = item_type_def_entry.get("item_type")
                    is_equippable = item_type_def_entry.get("is_equippable")
                    max_equippable = int_w_default(
                        item_type_def_entry.get("max_equippable"), -1) if dict_val_ne(item_type_def_entry,
                                                                                      'max_equippable') else -1
                    item_emoji_text = item_type_def_entry.get("emoji_text")
                    item_type_defs.append(ItemTypeDefinition(item_type=item_type,
                                                             is_equippable=is_equippable,
                                                             max_equippable=max_equippable,
                                                             emoji_text=item_emoji_text))
            skills = []
            if dict_val_ne(json_object, 'skills'):
                for game_skill_entry in json_object.get("skills"):
                    game_skill_name = game_skill_entry.get("skill_name")
                    game_skill_req = game_skill_entry.get("skill_req")
                    game_skill_restrict = game_skill_entry.get("skill_restrict")
                    game_skill_desc = game_skill_entry.get("skill_desc")
                    game_skill_mod_modifies_attributes = []
                    if dict_val_ne(game_skill_entry, 'modifies_attributes'):
                        for game_skill_mod_att_entry in game_skill_entry.get("modifies_attributes"):
                            game_skill_mod_att_name = game_skill_mod_att_entry.get("att_name")
                            game_skill_mod_mod_amt = int_w_default(game_skill_mod_att_entry.get("modification"), 0)
                            game_skill_mod_modifies_attributes.append(
                                AttributeModifier(att_name=game_skill_mod_att_name,
                                                  modification=game_skill_mod_mod_amt))
                    skills.append(Skill(skill_name=game_skill_name,
                                        skill_req=game_skill_req,
                                        skill_restrict=game_skill_restrict,
                                        skill_desc=game_skill_desc,
                                        modifies_attributes=game_skill_mod_modifies_attributes))
            status_modifiers = []
            if dict_val_ne(json_object, 'status_modifiers'):
                for status_mod_entry in json_object.get("status_modifiers"):
                    game_modifier_type = status_mod_entry.get("modifier_type")
                    game_modifier_name = status_mod_entry.get("modifier_name")
                    game_modifier_desc = status_mod_entry.get("modifier_desc")
                    game_modifier_duration = int_w_default(status_mod_entry.get("modifier_duration"), -1)
                    game_modifier_stacks = int_w_default(status_mod_entry.get("modifier_stacks"), 0)
                    game_stat_mod_modifies_attributes = []
                    if dict_val_ne(status_mod_entry, 'modifies_attributes'):
                        for game_stat_mod_att_entry in status_mod_entry.get("modifies_attributes"):
                            game_stat_mod_att_name = game_stat_mod_att_entry.get("att_name")
                            game_stat_mod_mod_amt = int_w_default(game_stat_mod_att_entry.get("modification"), 0)
                            game_stat_mod_modifies_attributes.append(AttributeModifier(att_name=game_stat_mod_att_name,
                                                                                       modification=game_stat_mod_mod_amt))
                    status_modifiers.append(StatusModifier(modifier_type=game_modifier_type,
                                                           modifier_name=game_modifier_name,
                                                           modifier_desc=game_modifier_desc,
                                                           modifier_duration=game_modifier_duration,
                                                           modifier_stacks=game_modifier_stacks,
                                                           modifies_attributes=game_stat_mod_modifies_attributes))
            pi_views = []
            if dict_val_ne(json_object, 'pi_views'):
                for piv_entry in json_object.get("pi_views"):
                    view_name = piv_entry.get("view_name")
                    channel_id = piv_entry.get("channel_id")
                    message_ids = list(piv_entry.get("message_ids"))
                    button_msg_id = piv_entry.get("button_msg_id")
                    pi_views.append(PersistentInteractableView(view_name=view_name,
                                                               channel_id=channel_id,
                                                               message_ids=message_ids,
                                                               button_msg_id=button_msg_id))
            actions = []
            items = []
            if dict_val_ne(json_object, 'players'):
                for player_entry in json_object.get("players"):
                    player_id = player_entry.get("player_id")
                    player_mod_channel = player_entry.get("player_mod_channel")
                    player_discord_name = player_entry.get("player_discord_name")
                    is_dead = player_entry.get("is_dead")
                    player_attributes = []
                    if dict_val_ne(player_entry, 'player_attributes'):
                        for attribute_entry in player_entry.get("player_attributes"):
                            attribute_name = attribute_entry.get("name")
                            attribute_level = int_w_default(attribute_entry.get("level"), 0)
                            attribute_max_level = int_w_default(attribute_entry.get("max_level"), -1)
                            player_attributes.append(Attribute(name=attribute_name,
                                                               level=attribute_level,
                                                               max_level=attribute_max_level))
                    player_resources = []
                    if dict_val_ne(player_entry, 'player_resources'):
                        for resource_entry in player_entry.get("player_resources"):
                            resource_type = resource_entry.get("resource_type")
                            resource_amt = int_w_default(resource_entry.get("resource_amt"), 0)
                            resource_income = int_w_default(resource_entry.get("resource_income"), 0)
                            resource_max = int_w_default(resource_entry.get("resource_max"), -1)
                            is_commodity = resource_entry.get("is_commodity")
                            is_perishable = resource_entry.get("is_perishable")
                            player_resources.append(Resource(resource_type=resource_type,
                                                             resource_amt=resource_amt,
                                                             resource_income=resource_income,
                                                             resource_max=resource_max,
                                                             is_commodity=is_commodity,
                                                             is_perishable=is_perishable))
                    player_skills = []
                    if dict_val_ne(player_entry, 'player_skills'):
                        for skill_entry in player_entry.get("player_skills"):
                            skill_name = skill_entry.get("skill_name")
                            skill_req = skill_entry.get("skill_req")
                            skill_restrict = skill_entry.get("skill_restrict")
                            skill_desc = skill_entry.get("skill_desc")
                            player_skill_modifies_attributes = []
                            if dict_val_ne(skill_entry, 'modifies_attributes'):
                                for player_skill_mod_att_entry in skill_entry.get("modifies_attributes"):
                                    player_skill_mod_att_name = player_skill_mod_att_entry.get("att_name")
                                    player_skill_mod_mod_amt = int_w_default(
                                        player_skill_mod_att_entry.get("modification"),
                                        0)
                                    player_skill_modifies_attributes.append(
                                        AttributeModifier(att_name=player_skill_mod_att_name,
                                                          modification=player_skill_mod_mod_amt))
                            player_skills.append(Skill(skill_name=skill_name,
                                                       skill_req=skill_req,
                                                       skill_restrict=skill_restrict,
                                                       skill_desc=skill_desc,
                                                       modifies_attributes=player_skill_modifies_attributes))
                    player_status_mods = []
                    if dict_val_ne(player_entry, 'player_status_mods'):
                        for player_status_mod_entry in player_entry.get("player_status_mods"):
                            modifier_type = player_status_mod_entry.get("modifier_type")
                            modifier_name = player_status_mod_entry.get("modifier_name")
                            modifier_desc = player_status_mod_entry.get("modifier_desc")
                            modifier_duration = int_w_default(player_status_mod_entry.get("modifier_duration"), -1)
                            modifier_stacks = int_w_default(player_status_mod_entry.get("modifier_stacks"), 0)
                            player_stat_mod_modifies_attributes = []
                            if dict_val_ne(player_status_mod_entry, 'modifies_attributes'):
                                for player_stat_mod_att_entry in player_status_mod_entry.get("modifies_attributes"):
                                    player_stat_mod_att_name = player_stat_mod_att_entry.get("att_name")
                                    player_stat_mod_mod_amt = int_w_default(
                                        player_stat_mod_att_entry.get("modification"), 0)
                                    player_stat_mod_modifies_attributes.append(
                                        AttributeModifier(att_name=player_stat_mod_att_name,
                                                          modification=player_stat_mod_mod_amt))
                            player_status_mods.append(StatusModifier(modifier_type=modifier_type,
                                                                     modifier_name=modifier_name,
                                                                     modifier_desc=modifier_desc,
                                                                     modifier_duration=modifier_duration,
                                                                     modifier_stacks=modifier_stacks,
                                                                     modifies_attributes=player_stat_mod_modifies_attributes))
                    player_actions = []
                    if dict_val_ne(player_entry, 'player_actions'):
                        for action_entry in player_entry.get("player_actions"):
                            action_name = action_entry.get("action_name")
                            player_action_costs = []
                            if dict_val_ne(action_entry, 'action_costs'):
                                for player_action_cost_entry in action_entry.get("action_costs"):
                                    player_res_cost_name = player_action_cost_entry.get("res_name")
                                    player_res_cost_amt = int_w_default(player_action_cost_entry.get("amount"), 0)
                                    player_action_costs.append(ResourceCost(res_name=player_res_cost_name,
                                                                            amount=player_res_cost_amt))
                            action_uses = int_w_default(action_entry.get("action_uses"), -1)
                            action_timing = action_entry.get("action_timing")
                            action_classes = action_entry.get("action_classes")
                            action_level_req = int_w_default(action_entry.get("action_level_req"), -1)
                            action_priority = int_w_default(action_entry.get("action_priority"), -1)
                            action_desc = action_entry.get("action_desc")
                            player_actions.append(Action(action_name=action_name,
                                                         action_timing=action_timing,
                                                         action_costs=player_action_costs,
                                                         action_uses=action_uses,
                                                         action_classes=action_classes,
                                                         action_level_req=action_level_req,
                                                         action_priority=action_priority,
                                                         action_desc=action_desc))
                    player_items = []
                    if dict_val_ne(player_entry, 'player_items'):
                        for item_entry in player_entry.get("player_items"):
                            item_name = item_entry.get("item_name")
                            item_type = item_entry.get("item_type")
                            item_subtype = item_entry.get("item_subtype")
                            item_rarity = item_entry.get("item_rarity")
                            item_properties = item_entry.get("item_properties")
                            item_desc = item_entry.get("item_desc")
                            is_equipped = item_entry.get("is_equipped")
                            item_action: Optional[Action] = None
                            if dict_val_ne(item_entry, 'item_action'):
                                player_item_action = item_entry.get("item_action")
                                item_action_name = player_item_action.get("action_name")
                                player_item_action_costs = []
                                if dict_val_ne(player_item_action, 'action_costs'):
                                    for player_item_action_cost_entry in player_item_action.get("action_costs"):
                                        player_item_action_cost_name = player_item_action_cost_entry.get("res_name")
                                        player_item_action_cost_amt = int_w_default(
                                            player_item_action_cost_entry.get("amount"), 0)
                                        player_item_action_costs.append(
                                            ResourceCost(res_name=player_item_action_cost_name,
                                                         amount=player_item_action_cost_amt))
                                item_action_uses = int_w_default(player_item_action.get("action_uses"), -1)
                                item_action_timing = player_item_action.get("action_timing")
                                item_action_classes = player_item_action.get("action_classes")
                                item_action_level_req = int_w_default(player_item_action.get("action_level_req"), -1)
                                item_action_priority = int_w_default(player_item_action.get("action_priority"), -1)
                                item_action_desc = player_item_action.get("action_desc")
                                item_action = Action(action_name=item_action_name,
                                                     action_timing=item_action_timing,
                                                     action_costs=player_item_action_costs,
                                                     action_uses=item_action_uses,
                                                     action_classes=item_action_classes,
                                                     action_level_req=item_action_level_req,
                                                     action_priority=item_action_priority,
                                                     action_desc=item_action_desc)
                            player_items.append(Item(item_name=item_name,
                                                     item_type=item_type,
                                                     item_subtype=item_subtype,
                                                     item_rarity=item_rarity,
                                                     item_properties=item_properties,
                                                     item_desc=item_desc,
                                                     is_equipped=is_equipped,
                                                     item_action=item_action))
                    players.append(Player(player_id=player_id,
                                          player_discord_name=player_discord_name,
                                          player_mod_channel=player_mod_channel,
                                          player_attributes=player_attributes,
                                          player_resources=player_resources,
                                          player_skills=player_skills,
                                          player_status_mods=player_status_mods,
                                          player_actions=player_actions,
                                          player_items=player_items,
                                          is_dead=is_dead))
            if dict_val_ne(json_object, 'rounds'):
                for round_entry in json_object.get("rounds"):
                    round_channel_id = round_entry.get("round_channel_id")
                    round_message_id = round_entry.get("round_message_id")
                    round_num = int_w_default(round_entry.get("round_number"))
                    is_active_round = round_entry.get("is_active_round")
                    votes = []
                    round_dilemmas = []
                    if dict_val_ne(round_entry, 'votes'):
                        for vote_entry in round_entry.get("votes"):
                            player_id = vote_entry.get("player_id")
                            choice = vote_entry.get("choice")
                            timestamp = vote_entry.get("timestamp")
                            votes.append(Vote(player_id=player_id,
                                              choice=choice,
                                              timestamp=timestamp))
                    if dict_val_ne(round_entry, 'round_dilemmas'):
                        for dilemma_entry in round_entry.get("round_dilemmas"):
                            dilemma_name = dilemma_entry.get("dilemma_name")
                            dilemma_channel_id = dilemma_entry.get("dilemma_channel_id")
                            dilemma_message_id = dilemma_entry.get("dilemma_message_id")
                            is_active_dilemma = dilemma_entry.get("is_active_dilemma")
                            dilemma_choices = set(dilemma_entry.get("dilemma_choices"))
                            dilemma_player_ids = set(dilemma_entry.get("dilemma_player_ids"))
                            dilemma_votes = []
                            if dict_val_ne(dilemma_entry, 'dilemma_votes'):
                                for dilemma_vote_entry in dilemma_entry.get("dilemma_votes"):
                                    player_id = dilemma_vote_entry.get("player_id")
                                    choice = dilemma_vote_entry.get("choice")
                                    timestamp = dilemma_vote_entry.get("timestamp")
                                    dilemma_votes.append(Vote(player_id=player_id,
                                                              choice=choice,
                                                              timestamp=timestamp))
                            round_dilemmas.append(Dilemma(dilemma_name=dilemma_name,
                                                          dilemma_channel_id=dilemma_channel_id,
                                                          dilemma_message_id=dilemma_message_id,
                                                          dilemma_player_ids=dilemma_player_ids,
                                                          dilemma_choices=dilemma_choices,
                                                          dilemma_votes=dilemma_votes,
                                                          is_active_dilemma=is_active_dilemma))
                    rounds.append(Round(round_number=round_num,
                                        round_channel_id=round_channel_id,
                                        round_message_id=round_message_id,
                                        round_dilemmas=round_dilemmas,
                                        is_active_round=is_active_round,
                                        votes=votes))
            if dict_val_ne(json_object, 'parties'):
                for party_entry in json_object.get("parties"):
                    channel_id = int_w_default(party_entry.get("channel_id"), 0)
                    max_size = int_w_default(party_entry.get("max_size"), -1)
                    party_name = party_entry.get("party_name")
                    player_ids = set(party_entry.get("player_ids"))
                    parties.append(Party(player_ids=player_ids,
                                         party_name=party_name,
                                         channel_id=channel_id,
                                         max_size=max_size))
            if dict_val_ne(json_object, 'actions'):
                for game_action_entry in json_object.get("actions"):
                    game_action_name = game_action_entry.get("action_name")
                    game_action_timing = game_action_entry.get("action_timing")
                    game_action_costs_resources = []
                    if dict_val_ne(game_action_entry, 'action_costs'):
                        for game_action_cost_entry in game_action_entry.get("action_costs"):
                            game_action_cost_name = game_action_cost_entry.get("res_name")
                            game_action_cost_amt = int_w_default(game_action_cost_entry.get("amount"), 0)
                            game_action_costs_resources.append(ResourceCost(res_name=game_action_cost_name,
                                                                            amount=game_action_cost_amt))
                    game_action_uses = int_w_default(game_action_entry.get("action_uses"), -1)
                    game_action_classes = game_action_entry.get("action_classes")
                    game_action_level_req = int_w_default(game_action_entry.get("action_level_req"), 0)
                    game_action_priority = int_w_default(game_action_entry.get("action_priority"), -1)
                    game_action_desc = game_action_entry.get("action_desc")
                    actions.append(Action(action_name=game_action_name,
                                          action_timing=game_action_timing,
                                          action_costs=game_action_costs_resources,
                                          action_uses=game_action_uses,
                                          action_classes=game_action_classes,
                                          action_level_req=game_action_level_req,
                                          action_priority=game_action_priority,
                                          action_desc=game_action_desc))
            if dict_val_ne(json_object, 'items'):
                for game_item_entry in json_object.get("items"):
                    game_item_name = game_item_entry.get("item_name")
                    game_item_type = game_item_entry.get("item_type")
                    game_item_subtype = game_item_entry.get("item_subtype")
                    game_item_rarity = game_item_entry.get("item_rarity")
                    game_item_properties = game_item_entry.get("item_properties")
                    game_is_equipped = game_item_entry.get("is_equipped")
                    game_item_desc = game_item_entry.get("item_desc")
                    game_item_action: Optional[Action] = None
                    if dict_val_ne(game_item_entry, 'item_action'):
                        game_item_action_entry = game_item_entry.get("item_action")
                        game_item_action_name = game_item_action_entry.get("action_name")
                        game_item_action_timing = game_item_action_entry.get("action_timing")
                        game_item_action_costs_resources = []
                        if dict_val_ne(game_item_action_entry, 'action_costs'):
                            for game_item_action_cost_entry in game_item_action_entry.get("action_costs"):
                                game_item_action_cost_name = game_item_action_cost_entry.get("res_name")
                                game_item_action_cost_amt = int_w_default(game_item_action_cost_entry.get("amount"), 0)
                                game_item_action_costs_resources.append(
                                    ResourceCost(res_name=game_item_action_cost_name,
                                                 amount=game_item_action_cost_amt))
                        game_item_action_uses = int_w_default(game_item_action_entry.get("action_uses"), -1)
                        game_item_action_classes = game_item_action_entry.get("action_classes")
                        game_item_action_level_req = int_w_default(game_item_action_entry.get("action_level_req"), 0)
                        game_item_action_priority = int_w_default(game_item_action_entry.get("action_priority"), -1)
                        game_item_action_desc = game_item_action_entry.get("action_desc")
                        game_item_action = Action(action_name=game_item_action_name,
                                                  action_timing=game_item_action_timing,
                                                  action_costs=game_item_action_costs_resources,
                                                  action_uses=game_item_action_uses,
                                                  action_classes=game_item_action_classes,
                                                  action_level_req=game_item_action_level_req,
                                                  action_priority=game_item_action_priority,
                                                  action_desc=game_item_action_desc)
                    items.append(Item(item_name=game_item_name,
                                      item_type=game_item_type,
                                      item_subtype=game_item_subtype,
                                      item_rarity=game_item_rarity,
                                      item_properties=game_item_properties,
                                      item_desc=game_item_desc,
                                      is_equipped=game_is_equipped,
                                      item_action=game_item_action))
            return Game(is_active=is_active,
                        parties_locked=parties_locked,
                        voting_locked=voting_locked,
                        items_locked=items_locked,
                        resources_locked=resources_locked,
                        players=players,
                        rounds=rounds,
                        parties=parties,
                        attribute_definitions=attribute_defs,
                        resource_definitions=resource_defs,
                        item_type_definitions=item_type_defs,
                        skills=skills,
                        status_modifiers=status_modifiers,
                        actions=actions,
                        items=items,
                        pi_views=pi_views)
    except Exception as e:
        logger.error(f'Error while reading dom file!\n{e}')


def write_dom_to_json(game: Game):
    millis_prefix = round(time.time() * 1000)
    filepath_final = f'{Conf.BASE_PATH}/{Conf.GAME_FILE}'
    filepath_temp = f'{Conf.BASE_PATH}/{millis_prefix}_{Conf.GAME_FILE}'

    with open(filepath_temp, 'w', encoding="utf8") as outfile:

        # convert Game to dictionary here
        game_dict = {"is_active": game.is_active,
                     "parties_locked": game.parties_locked,
                     "voting_locked": game.voting_locked,
                     "items_locked": game.items_locked,
                     "resources_locked": game.resources_locked}
        att_def_dicts = []
        for att_def in game.attribute_definitions:
            att_def_dicts.append({"attribute_name": att_def.attribute_name,
                                  "attribute_max": att_def.attribute_max,
                                  "emoji_text": att_def.emoji_text})
        game_dict["attribute_defs"] = att_def_dicts
        res_def_dicts = []
        for res_def in game.resource_definitions:
            res_def_dicts.append({"resource_name": res_def.resource_name,
                                  "resource_max": res_def.resource_max,
                                  "is_commodity": res_def.is_commodity,
                                  "is_perishable": res_def.is_perishable,
                                  "emoji_text": res_def.emoji_text})
        game_dict["resource_defs"] = res_def_dicts
        item_type_def_dicts = []
        for item_type_def in game.item_type_definitions:
            item_type_def_dicts.append({"item_type": item_type_def.item_type,
                                        "is_equippable": item_type_def.is_equippable,
                                        "max_equippable": item_type_def.max_equippable,
                                        "emoji_text": item_type_def.emoji_text})
        game_dict["item_type_defs"] = item_type_def_dicts
        game_skill_dicts = []
        for game_skill in game.skills:
            game_skill_modifies_atts_dicts = []
            if game_skill.modifies_attributes is not None:
                for game_skill_modifies_atts in game_skill.modifies_attributes:
                    game_skill_modifies_atts_dicts.append({"att_name": game_skill_modifies_atts.att_name,
                                                           "modification": game_skill_modifies_atts.modification})
            game_skill_dicts.append({"skill_name": game_skill.skill_name,
                                     "skill_req": game_skill.skill_req,
                                     "skill_restrict": game_skill.skill_restrict,
                                     "skill_desc": game_skill.skill_desc,
                                     "modifies_attributes": game_skill_modifies_atts_dicts})
        game_dict["skills"] = game_skill_dicts
        game_stat_mod_dicts = []
        for game_stat_mod in game.status_modifiers:
            game_stat_mod_modifies_atts_dicts = []
            if game_stat_mod.modifies_attributes is not None:
                for game_stat_mod_modifies_atts in game_stat_mod.modifies_attributes:
                    game_stat_mod_modifies_atts_dicts.append({"att_name": game_stat_mod_modifies_atts.att_name,
                                                              "modification": game_stat_mod_modifies_atts.modification})
            game_stat_mod_dicts.append({"modifier_type": game_stat_mod.modifier_type,
                                        "modifier_name": game_stat_mod.modifier_name,
                                        "modifier_desc": game_stat_mod.modifier_desc,
                                        "modifier_duration": game_stat_mod.modifier_duration,
                                        "modifier_stacks": game_stat_mod.modifier_stacks,
                                        "modifies_attributes": game_stat_mod_modifies_atts_dicts})
        game_dict["status_mods"] = game_stat_mod_dicts
        game_pi_view_dicts = []
        for pi_view in game.pi_views:
            game_pi_view_dicts.append({"view_name": pi_view.view_name,
                                       "channel_id": pi_view.channel_id,
                                       "message_ids": pi_view.message_ids,
                                       "button_msg_id": pi_view.button_msg_id})
        game_dict["pi_views"] = game_pi_view_dicts
        player_dicts = []
        for player in game.players:
            player_attribute_dicts = []
            for attribute in player.player_attributes:
                player_attribute_dicts.append({"name": attribute.name,
                                               "level": attribute.level,
                                               "max_level": attribute.max_level})
            player_resource_dicts = []
            for resource in player.player_resources:
                player_resource_dicts.append({"resource_type": resource.resource_type,
                                              "resource_amt": resource.resource_amt,
                                              "resource_income": resource.resource_income,
                                              "resource_max": resource.resource_max,
                                              "is_commodity": resource.is_commodity,
                                              "is_perishable": resource.is_perishable})
            player_skill_dicts = []
            for skill in player.player_skills:
                skill_modifies_atts_dicts = []
                if skill.modifies_attributes is not None:
                    for skill_modifies_atts in skill.modifies_attributes:
                        skill_modifies_atts_dicts.append({"att_name": skill_modifies_atts.att_name,
                                                          "modification": skill_modifies_atts.modification})
                player_skill_dicts.append({"skill_name": skill.skill_name,
                                           "skill_req": skill.skill_req,
                                           "skill_restrict": skill.skill_restrict,
                                           "skill_desc": skill.skill_desc,
                                           "modifies_attributes": skill_modifies_atts_dicts})
            player_status_mod_dicts = []
            for status_mod in player.player_status_mods:
                stat_mod_modifies_atts_dicts = []
                if status_mod.modifies_attributes is not None:
                    for stat_mod_modifies_atts in status_mod.modifies_attributes:
                        stat_mod_modifies_atts_dicts.append({"att_name": stat_mod_modifies_atts.att_name,
                                                             "modification": stat_mod_modifies_atts.modification})
                player_status_mod_dicts.append({"modifier_type": status_mod.modifier_type,
                                                "modifier_name": status_mod.modifier_name,
                                                "modifier_desc": status_mod.modifier_desc,
                                                "modifier_duration": status_mod.modifier_duration,
                                                "modifier_stacks": status_mod.modifier_stacks,
                                                "modifies_attributes": stat_mod_modifies_atts_dicts})
            player_action_dicts = []
            for player_action in player.player_actions:
                player_action_cost_dicts = []
                if player_action.action_costs is not None:
                    for player_action_cost in player_action.action_costs:
                        player_action_cost_dicts.append({"res_name": player_action_cost.res_name,
                                                         "amount": player_action_cost.amount})
                player_action_dicts.append({"action_name": player_action.action_name,
                                            "action_costs": player_action_cost_dicts,
                                            "action_uses": player_action.action_uses,
                                            "action_timing": player_action.action_timing,
                                            "action_classes": player_action.action_classes,
                                            "action_level_req": player_action.action_level_req,
                                            "action_priority": player_action.action_priority,
                                            "action_desc": player_action.action_desc})
            player_item_dicts = []
            for player_item in player.player_items:
                player_item_action_dict = {}
                if player_item.item_action is not None:
                    player_item_action: Action = player_item.item_action
                    player_item_action_cost_dicts = []
                    if player_item_action.action_costs is not None:
                        for player_item_action_cost in player_item_action.action_costs:
                            player_item_action_cost_dicts.append({"res_name": player_item_action_cost.res_name,
                                                                  "amount": player_item_action_cost.amount})
                    player_item_action_dict = {"action_name": player_item_action.action_name,
                                               "action_costs": player_item_action_cost_dicts,
                                               "action_uses": player_item_action.action_uses,
                                               "action_timing": player_item_action.action_timing,
                                               "action_classes": player_item_action.action_classes,
                                               "action_level_req": player_item_action.action_level_req,
                                               "action_priority": player_item_action.action_priority,
                                               "action_desc": player_item_action.action_desc}
                player_item_dicts.append({"item_name": player_item.item_name,
                                          "item_type": player_item.item_type,
                                          "item_subtype": player_item.item_subtype,
                                          "item_rarity": player_item.item_rarity,
                                          "item_properties": player_item.item_properties,
                                          "item_desc": player_item.item_descr,
                                          "item_action": player_item_action_dict})
            player_dicts.append({"player_id": player.player_id,
                                 "player_discord_name": player.player_discord_name,
                                 "player_mod_channel": player.player_mod_channel,
                                 "player_attributes": player_attribute_dicts,
                                 "player_resources": player_resource_dicts,
                                 "player_skills": player_skill_dicts,
                                 "player_status_mods": player_status_mod_dicts,
                                 "player_actions": player_action_dicts,
                                 "player_items": player_item_dicts,
                                 "is_dead": player.is_dead
                                 })
        game_dict["players"] = player_dicts
        round_dicts = []
        for a_round in game.rounds:
            vote_dicts = []
            dilemma_dicts = []
            for vote in a_round.votes:
                vote_dicts.append({"player_id": vote.player_id,
                                   "choice": vote.choice,
                                   "timestamp": vote.timestamp})
            for a_dilemma in a_round.round_dilemmas:
                dilemma_vote_dicts = []
                for dilemma_vote in a_dilemma.dilemma_votes:
                    dilemma_vote_dicts.append({"player_id": dilemma_vote.player_id,
                                               "choice": dilemma_vote.choice,
                                               "timestamp": dilemma_vote.timestamp})
                dilemma_dicts.append({"dilemma_name": a_dilemma.dilemma_name,
                                      "dilemma_channel_id": a_dilemma.dilemma_channel_id,
                                      "dilemma_message_id": a_dilemma.dilemma_message_id,
                                      "dilemma_player_ids": list(a_dilemma.dilemma_player_ids),
                                      "dilemma_choices": list(a_dilemma.dilemma_choices),
                                      "dilemma_votes": dilemma_vote_dicts,
                                      "is_active_dilemma": a_dilemma.is_active_dilemma})
            round_dicts.append({"round_number": a_round.round_number,
                                "round_channel_id": a_round.round_channel_id,
                                "round_message_id": a_round.round_message_id,
                                "is_active_round": a_round.is_active_round,
                                "votes": vote_dicts,
                                "round_dilemmas": dilemma_dicts})
        game_dict["rounds"] = round_dicts
        party_dicts = []
        for a_party in game.parties:
            party_dicts.append({"player_ids": list(a_party.player_ids),
                                "party_name": a_party.party_name,
                                "channel_id": a_party.channel_id,
                                "max_size": a_party.max_size})
        game_dict["parties"] = party_dicts
        game_action_dicts = []
        for game_action in game.actions:
            game_action_cost_dicts = []
            for game_action_cost in game_action.action_costs:
                game_action_cost_dicts.append({"res_name": game_action_cost.res_name,
                                               "amount": game_action_cost.amount})
            game_action_dicts.append({"action_name": game_action.action_name,
                                      "action_costs": game_action_cost_dicts,
                                      "action_uses": game_action.action_uses,
                                      "action_timing": game_action.action_timing,
                                      "action_classes": game_action.action_classes,
                                      "action_level_req": game_action.action_level_req,
                                      "action_priority": game_action.action_priority,
                                      "action_desc": game_action.action_desc})
        game_dict["actions"] = game_action_dicts
        game_item_dicts = []
        for game_item in game.items:
            game_item_action_dict = {}
            if game_item.item_action is not None:
                game_item_action: Action = game_item.item_action
                game_item_action_cost_dicts = []
                if game_item_action.action_costs is not None:
                    for game_item_action_cost in game_item_action.action_costs:
                        game_item_action_cost_dicts.append({"res_name": game_item_action_cost.res_name,
                                                            "amount": game_item_action_cost.amount})
                game_item_action_dict = {"action_name": game_item_action.action_name,
                                         "action_costs": game_item_action_cost_dicts,
                                         "action_uses": game_item_action.action_uses,
                                         "action_timing": game_item_action.action_timing,
                                         "action_classes": game_item_action.action_classes,
                                         "action_level_req": game_item_action.action_level_req,
                                         "action_priority": game_item_action.action_priority,
                                         "action_desc": game_item_action.action_desc}
            game_item_dicts.append({"item_name": game_item.item_name,
                                    "item_type": game_item.item_type,
                                    "item_subtype": game_item.item_subtype,
                                    "item_rarity": game_item.item_rarity,
                                    "item_properties": game_item.item_properties,
                                    "item_desc": game_item.item_descr,
                                    "item_action": game_item_action_dict})
        game_dict["items"] = game_item_dicts
        json.dump(game_dict, outfile, indent=2, ensure_ascii=False)
        outfile.close()

        if os.path.isfile(filepath_final):
            os.remove(filepath_final)
        os.rename(filepath_temp, filepath_final)

        logger.info(f'Wrote game data to {filepath_final}')


async def get_game(file_path: str) -> Game:
    logger.info(f'Grabbing game info from {file_path}')
    return read_json_to_dom(filepath=file_path)


async def write_game(game: Game):
    write_dom_to_json(game=game)


async def read_players_file(file_path: str, game_attribute_definitions: Dict[str, AttributeDefinition] = None,
                            game_resource_definitions: Dict[str, ResourceDefinition] = None,
                            game_status_modifiers: Dict[str, StatusModifier] = None,
                            game_skills: Dict[str, Skill] = None, game_actions: Dict[str, Action] = None,
                            game_items: Dict[str, Item] = None) -> List[Player]:
    if game_attribute_definitions is None:
        game_attribute_definitions = {}
    if game_resource_definitions is None:
        game_resource_definitions = {}
    if game_status_modifiers is None:
        game_status_modifiers = {}
    if game_skills is None:
        game_skills = {}
    if game_actions is None:
        game_actions = {}
    if game_items is None:
        game_items = {}

    players = []

    rows: List[Dict] = await read_csv_file(file_path=file_path)

    for row in rows:
        player_id = int(row['player_id'])
        player_discord_name = row['name']
        player_mod_channel = int(row['mod_channel']) if dict_val_ne(row, 'mod_channel') else None
        player_attributes_str = row['attributes'] if dict_val_ne(row, 'attributes') else None
        player_resources_str = row['resources'] if dict_val_ne(row, 'resources') else None
        player_skills_str = row['skills'] if dict_val_ne(row, 'skills') else None
        player_status_modifiers_str = row['status_modifiers'] if dict_val_ne(row, 'status_modifiers') else None
        player_actions_str = row['actions'] if dict_val_ne(row, 'actions') else None
        player_items_str = row['items'] if dict_val_ne(row, 'items') else None

        player_attributes: List[Attribute] = []
        player_resources: List[Resource] = []
        player_skills: List[Skill] = []
        player_status_modifiers: List[StatusModifier] = []
        player_actions: List[Action] = []
        player_items: List[Item] = []

        if player_attributes_str is not None:
            player_attributes_list = list(filter(None, player_attributes_str.split(';')))
            for player_attribute in player_attributes_list:
                player_attribute_split = player_attribute.split(':')
                player_attribute_name = player_attribute_split[0]
                player_attribute_count = int(player_attribute_split[1])
                if player_attribute_name in game_attribute_definitions:
                    player_attributes.append(Attribute(name=player_attribute_name,
                                                       level=player_attribute_count,
                                                       max_level=game_attribute_definitions[
                                                           player_attribute_name].attribute_max))
                else:
                    logger.warn(
                        f'Attribute type of {player_attribute_name} was not defined in game files! Ignoring this attribute...')

        if player_resources_str is not None:
            player_resources_list = list(filter(None, player_resources_str.split(';')))
            for player_resource in player_resources_list:
                player_resource_split = player_resource.split(':')
                player_resource_name = player_resource_split[0]
                player_resource_count = int(player_resource_split[1])
                player_resource_income = int(player_resource_split[2])
                if player_resource_name in game_resource_definitions:
                    player_resources.append(Resource(resource_type=player_resource_name,
                                                     resource_amt=player_resource_count,
                                                     resource_income=player_resource_income,
                                                     resource_max=game_resource_definitions[
                                                         player_resource_name].resource_max,
                                                     is_commodity=game_resource_definitions[
                                                         player_resource_name].is_commodity,
                                                     is_perishable=game_resource_definitions[
                                                         player_resource_name].is_perishable))

        if player_skills_str is not None:
            player_skills_list = list(filter(None, player_skills_str.split(';')))
            for player_skill_name in player_skills_list:
                if player_skill_name in game_skills:
                    player_skills.append(game_skills[player_skill_name])

        if player_status_modifiers_str is not None:
            player_status_modifiers_list = list(filter(None, player_status_modifiers_str.split(';')))
            for player_status_modifier_name in player_status_modifiers_list:
                if player_status_modifier_name in game_status_modifiers:
                    player_status_modifiers.append(game_status_modifiers[player_status_modifier_name])

        if player_actions_str is not None:
            player_action_name_list = list(filter(None, player_actions_str.split(';')))
            for player_action_name in player_action_name_list:
                if player_action_name in game_actions:
                    player_actions.append(game_actions[player_action_name])

        if player_items_str is not None:
            player_item_name_list = list(filter(None, player_items_str.split(';')))
            for player_item_name in player_item_name_list:
                if player_item_name in game_items:
                    player_items.append(game_items[player_item_name])

        players.append(Player(player_id=player_id,
                              player_discord_name=player_discord_name,
                              player_mod_channel=player_mod_channel,
                              player_resources=player_resources,
                              player_attributes=player_attributes,
                              player_skills=player_skills,
                              player_status_mods=player_status_modifiers,
                              player_actions=player_actions,
                              player_items=player_items,
                              is_dead=False))

    return players


async def read_parties_file(file_path: str) -> List[Party]:
    parties = []

    rows: List[Dict] = await read_csv_file(file_path=file_path)

    for row in rows:
        player_ids = set(map(int, list(filter(None, row['player_ids'].split(';'))))) if dict_val_ne(row,
                                                                                                    'player_ids') else []
        party_name = row['name']
        max_size = int_w_default(row['max_size'], -1) if dict_val_ne(row, 'max_size') else -1
        channel_id = int_w_default(row['channel_id'], 0) if dict_val_ne(row, 'channel_id') else 0
        parties.append(Party(player_ids=player_ids,
                             party_name=party_name,
                             max_size=max_size,
                             channel_id=channel_id))
    return parties


async def read_attribute_definitions_file(file_path: str) -> List[AttributeDefinition]:
    attribute_definitions = []

    rows: List[Dict] = await read_csv_file(file_path=file_path)

    for row in rows:
        attribute_name = row['attribute_name']
        attribute_max = int_w_default(row['attribute_max'], -1) if dict_val_ne(row, 'attribute_max') else -1
        emoji_text = row['emoji_text'] if dict_val_ne(row, 'emoji_text') else None
        attribute_definitions.append(AttributeDefinition(attribute_name=attribute_name,
                                                         attribute_max=attribute_max,
                                                         emoji_text=emoji_text))

    return attribute_definitions


async def read_resource_definitions_file(file_path: str) -> List[ResourceDefinition]:
    resource_definitions = []

    rows: List[Dict] = await read_csv_file(file_path=file_path)

    for row in rows:
        resource_name = row['resource_name']
        resource_max = int_w_default(row['resource_max'], -1) if dict_val_ne(row, 'resource_max') else -1
        is_commodity = True if dict_val_ne(row, 'is_commodity') and row['is_commodity'] == 'True' else False
        is_perishable = True if dict_val_ne(row, 'is_perishable') and row['is_perishable'] == 'True' else False
        emoji_text = row['emoji_text'] if dict_val_ne(row, 'emoji_text') else None
        resource_definitions.append(ResourceDefinition(resource_name=resource_name,
                                                       resource_max=resource_max,
                                                       is_commodity=is_commodity,
                                                       is_perishable=is_perishable,
                                                       emoji_text=emoji_text))

    return resource_definitions


async def read_item_type_definitions_file(file_path: str) -> List[ItemTypeDefinition]:
    item_type_definitions = []

    rows: List[Dict] = await read_csv_file(file_path=file_path)

    for row in rows:
        item_type = row['item_type']
        is_equippable = True if dict_val_ne(row, 'is_equippable') and row['is_equippable'] == 'True' else False
        max_equippable = int_w_default(row['max_equippable'], 0) if dict_val_ne(row, 'max_equippable') else 0
        emoji_text = row['emoji_text'] if dict_val_ne(row, 'emoji_text') else None
        item_type_definitions.append(ItemTypeDefinition(item_type=item_type,
                                                        is_equippable=is_equippable,
                                                        max_equippable=max_equippable,
                                                        emoji_text=emoji_text))

    return item_type_definitions


async def read_skills_file(file_path: str) -> List[Skill]:
    skills = []

    rows: List[Dict] = await read_csv_file(file_path=file_path)

    for row in rows:
        skill_name = row['skill_name']
        skill_req = row['skill_req'] if dict_val_ne(row, 'skill_req') else None
        skill_restrict = row['skill_restrict'] if dict_val_ne(row, 'skill_restrict') else None
        skill_desc = row['skill_desc']
        modifies_attributes_raw = list(filter(None, row['modifies_attributes'].split(';'))) if dict_val_ne(row,
                                                                                                           'modifies_attributes') else []

        modifies_attributes = []
        for entry in modifies_attributes_raw:
            entry_splits = list(filter(None, entry.split(':')))
            modifies_attributes.append(AttributeModifier(att_name=entry_splits[0], modification=int(entry_splits[1])))

        skills.append(Skill(skill_name=skill_name,
                            skill_req=skill_req,
                            skill_restrict=skill_restrict,
                            skill_desc=skill_desc,
                            modifies_attributes=modifies_attributes))

    return skills


async def read_status_modifiers_file(file_path: str) -> List[StatusModifier]:
    status_modifiers = []

    rows: List[Dict] = await read_csv_file(file_path=file_path)

    for row in rows:
        modifier_type = row['modifier_type']
        modifier_name = row['modifier_name']
        modifier_desc = row['modifier_desc']
        modifier_duration = int_w_default(row['modifier_duration'], -1) if dict_val_ne(row, 'modifier_duration') else -1
        modifier_stacks = int_w_default(row['modifier_stacks'], 0) if dict_val_ne(row, 'modifier_stacks') else 0
        modifies_attributes_raw = list(
            filter(None, row['modifies_attributes'].split(';'))) if dict_val_ne(row, 'modifies_attributes') else []

        modifies_attributes = []
        for entry in modifies_attributes_raw:
            entry_splits = list(filter(None, entry.split(':')))
            modifies_attributes.append(AttributeModifier(att_name=entry_splits[0], modification=int(entry_splits[1])))

        status_modifiers.append(StatusModifier(modifier_type=modifier_type,
                                               modifier_name=modifier_name,
                                               modifier_desc=modifier_desc,
                                               modifier_duration=modifier_duration,
                                               modifier_stacks=modifier_stacks,
                                               modifies_attributes=modifies_attributes))

    return status_modifiers


async def read_actions_file(file_path: str) -> List[Action]:
    actions = []

    rows: List[Dict] = await read_csv_file(file_path=file_path)

    for row in rows:
        action_name = row['action_name']
        action_timing = row['action_timing'] if dict_val_ne(row, 'action_timing') else None
        action_costs_raw = list(filter(None, row['action_costs'].split(';'))) if dict_val_ne(row,
                                                                                             'action_costs') else []

        action_costs = []
        for entry in action_costs_raw:
            entry_splits = list(filter(None, entry.split(':')))
            action_costs.append(ResourceCost(res_name=entry_splits[0], amount=int(entry_splits[1])))

        action_uses = int_w_default(row['action_uses'], -1)
        action_classes = list(filter(None, row['action_classes'].split(';'))) if dict_val_ne(row,
                                                                                             'action_classes') else []
        action_level_req = int_w_default(row['action_level_req'], 0) if dict_val_ne(row, 'action_level_req') else 0
        action_priority = int_w_default(row['action_priority'], -1) if dict_val_ne(row, 'action_priority') else -1
        action_desc = row['action_desc']
        actions.append(Action(action_name=action_name,
                              action_timing=action_timing,
                              action_costs=action_costs,
                              action_uses=action_uses,
                              action_classes=action_classes,
                              action_level_req=action_level_req,
                              action_priority=action_priority,
                              action_desc=action_desc))

    return actions


async def read_items_file(file_path: str, game_actions: Dict[str, Action] = None) -> List[Item]:
    if game_actions is None:
        game_actions = {}
    items = []

    rows: List[Dict] = await read_csv_file(file_path=file_path)

    for row in rows:
        item_name = row['item_name']
        item_type = row['item_type']
        item_subtype = row['item_subtype'] if dict_val_ne(row, 'item_subtype') else None
        item_rarity = row['item_rarity'] if dict_val_ne(row, 'item_rarity') else None
        item_properties = row['item_properties'] if dict_val_ne(row, 'item_properties') else None
        item_desc = row['item_desc']
        is_equipped = True if dict_val_ne(row, 'is_equipped') and row['is_equipped'] == 'True' else False
        item_action_name = row['action_name'] if dict_val_ne(row, 'action_name') else None

        item_action: Optional[Action] = None
        if item_action_name is not None and item_action_name in game_actions:
            item_action = game_actions[item_action_name]

        items.append(Item(item_name=item_name,
                          item_type=item_type,
                          item_subtype=item_subtype,
                          item_rarity=item_rarity,
                          item_properties=item_properties,
                          item_desc=item_desc,
                          is_equipped=is_equipped,
                          item_action=item_action))

    return items


async def read_csv_file(file_path: str) -> List[Dict]:
    rows: List[Dict] = []
    with open(file_path, newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)

        for row in map(dict, reader):
            rows.append(row)

    return rows


def dict_val_ne(the_dict: dict, the_key: str) -> bool:
    if the_key in the_dict:
        if the_dict[the_key]:
            return True
        else:
            return False
    else:
        return False


def int_w_default(value, default=0) -> int:
    try:
        if value is None or value == "":
            return default
        else:
            return value if isinstance(value, int) else int(value)
    except Exception as e:
        logger.warn(f"Value {value} was invalid; replaced with default {default}")
        logger.warn(f'Traceback: {traceback.format_stack(limit=10)}')
        return default
