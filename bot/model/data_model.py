#! data_model.py
# Pydantic data models for managing game state
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Set
from bot.botlogger.logging_manager import logger
import csv
import json
import os
import time
import traceback
from bot.model.conf_vars import ConfVars as Conf


class PersistentInteractableView(BaseModel):
    view_name: str
    channel_id: int
    message_ids: List[int]
    button_msg_id: int


class AttributeModifier(BaseModel):
    att_name: str
    modification: int


class Attribute(BaseModel):
    name: str
    level: int
    max_level: Optional[int] = -1


class ResourceCost(BaseModel):
    res_name: str
    amount: int


class Resource(BaseModel):
    resource_type: str
    resource_amt: int
    resource_income: Optional[int] = 0
    resource_max: Optional[int] = -1
    is_commodity: bool = False
    is_perishable: bool = False


class Skill(BaseModel):
    skill_name: str
    skill_req: Optional[str] = None
    skill_restrict: Optional[str] = None
    skill_desc: str
    modifies_attributes: List[AttributeModifier] = Field(default_factory=list)


class StatusModifier(BaseModel):
    modifier_type: str
    modifier_name: str
    modifier_desc: Optional[str] = None
    modifier_duration: Optional[int] = -1
    modifier_stacks: Optional[int] = -1
    modifies_attributes: List[AttributeModifier] = Field(default_factory=list)


class Action(BaseModel):
    action_name: str
    action_type: Optional[str] = None
    action_timing: Optional[str] = None
    action_costs: List[ResourceCost] = Field(default_factory=list)
    action_uses: Optional[int] = -1
    action_classes: List[str] = Field(default_factory=list)
    action_level_req: Optional[int] = 0
    action_priority: Optional[int]
    action_desc: str


class Item(BaseModel):
    item_name: str
    item_type: str
    item_subtype: Optional[str] = None
    item_rarity: Optional[str] = None
    item_properties: Optional[str] = None
    item_desc: Optional[str] = None
    is_equipped: bool = False
    item_action: Optional[Action] = None


class Player(BaseModel):
    player_id: int
    player_discord_name: str
    player_mod_channel: Optional[int] = None
    player_resources: List[Resource] = Field(default_factory=list)
    player_attributes: List[Attribute] = Field(default_factory=list)
    player_status_mods: List[StatusModifier] = Field(default_factory=list)
    player_skills: List[Skill] = Field(default_factory=list)
    player_actions: List[Action] = Field(default_factory=list)
    player_items: List[Item] = Field(default_factory=list)
    is_dead: bool = False

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


class Vote(BaseModel):
    player_id: int
    choice: str
    timestamp: int


class Dilemma(BaseModel):
    dilemma_votes: List[Vote] = Field(default_factory=list)
    dilemma_name: str
    dilemma_channel_id: int
    dilemma_message_id: int
    dilemma_player_ids: Set[int] = Field(default_factory=set)
    dilemma_choices: Set[str] = Field(default_factory=set)
    is_active_dilemma: bool

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


class Party(BaseModel):
    player_ids: Set[int] = Field(default_factory=set)
    party_name: str
    max_size: int
    channel_id: int

    def add_player(self, player: Player):
        self.player_ids.add(player.player_id)

    def remove_player(self, player: Player):
        self.player_ids.remove(player.player_id)


class Round(BaseModel):
    votes: List[Vote] = Field(default_factory=list)
    round_channel_id: int
    round_message_id: int
    round_number: int
    round_dilemmas: List[Dilemma] = Field(default_factory=list)
    is_active_round: bool

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


class AttributeDefinition(BaseModel):
    attribute_name: str
    attribute_max: int = -1
    emoji_text: Optional[str] = None


class ResourceDefinition(BaseModel):
    resource_name: str
    resource_max: int = -1
    is_commodity: bool
    is_perishable: bool
    emoji_text: Optional[str] = None


class ItemTypeDefinition(BaseModel):
    item_type: str
    is_equippable: bool
    max_equippable: int
    emoji_text: Optional[str] = None


class ActionTypeDefinition(BaseModel):
    action_type: str
    emoji_text: Optional[str] = None


class Game(BaseModel):
    model_config = {'populate_by_name': True}
    
    is_active: bool
    parties_locked: bool
    voting_locked: bool
    items_locked: bool
    resources_locked: bool
    players: List[Player] = Field(default_factory=list)
    parties: List[Party] = Field(default_factory=list)
    rounds: List[Round] = Field(default_factory=list)
    action_type_definitions: List[ActionTypeDefinition] = Field(default_factory=list, alias='action_type_defs')
    item_type_definitions: List[ItemTypeDefinition] = Field(default_factory=list, alias='item_type_defs')
    resource_definitions: List[ResourceDefinition] = Field(default_factory=list, alias='resource_defs')
    attribute_definitions: List[AttributeDefinition] = Field(default_factory=list, alias='attribute_defs')
    skills: List[Skill] = Field(default_factory=list)
    status_modifiers: List[StatusModifier] = Field(default_factory=list, alias='status_mods')
    actions: List[Action] = Field(default_factory=list)
    items: List[Item] = Field(default_factory=list)
    pi_views: List[PersistentInteractableView] = Field(default_factory=list)

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

    def get_action_type_definitions(self) -> Dict[str, ActionTypeDefinition]:
        action_type_def_dict: Dict[str, ActionTypeDefinition] = {}
        for action_type_def in self.action_type_definitions:
            action_type_def_dict[action_type_def.action_type] = action_type_def
        return action_type_def_dict

    def get_action_type_definition_by_name(self, action_type: str) -> Optional[ActionTypeDefinition]:
        for action_type_def in self.action_type_definitions:
            if action_type_def.action_type == action_type:
                return action_type_def
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


# Legacy mapping functions - replaced by Pydantic models in Game class methods


def read_json_to_dom(filepath: str) -> Game:
    try:
        with open(filepath, 'r', encoding="utf8") as openfile:
            json_data = json.load(openfile)
            return Game.model_validate(json_data)
    except Exception as e:
        logger.error(f'Error while reading game file from {filepath}: {e}')
        raise


def write_dom_to_json(game: Game):
    millis_prefix = round(time.time() * 1000)
    filepath_final = f'{Conf.BASE_PATH}/{Conf.GAME_FILE}'
    filepath_temp = f'{Conf.BASE_PATH}/{millis_prefix}_{Conf.GAME_FILE}'

    try:
        with open(filepath_temp, 'w', encoding="utf8") as outfile:
            json_data = game.model_dump_json(indent=2, by_alias=True)
            outfile.write(json_data)

        if os.path.isfile(filepath_final):
            os.remove(filepath_final)
        os.rename(filepath_temp, filepath_final)

        logger.info(f'Wrote game data to {filepath_final}')
    except Exception as e:
        logger.error(f'Error writing game file to {filepath_final}: {e}')
        raise


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
    rows: List[Dict] = await read_csv_file(file_path=file_path)
    parties = []
    
    for row in rows:
        cleaned_row = clean_csv_row(row)
        
        # Parse player_ids field if present
        if cleaned_row.get('player_ids'):
            player_ids_raw = list(filter(None, cleaned_row['player_ids'].split(';')))
            cleaned_row['player_ids'] = list(map(int, player_ids_raw))
        
        # Map 'name' field to 'party_name' for Pydantic model
        if cleaned_row.get('name'):
            cleaned_row['party_name'] = cleaned_row.pop('name')
        
        # Let Pydantic handle validation and defaults
        party = Party.model_validate(cleaned_row)
        parties.append(party)
    
    return parties


async def read_attribute_definitions_file(file_path: str) -> List[AttributeDefinition]:
    rows: List[Dict] = await read_csv_file(file_path=file_path)
    attribute_definitions = []
    
    for row in rows:
        cleaned_row = clean_csv_row(row)
        # Let Pydantic handle validation and defaults
        attribute_def = AttributeDefinition.model_validate(cleaned_row)
        attribute_definitions.append(attribute_def)
    
    return attribute_definitions


async def read_resource_definitions_file(file_path: str) -> List[ResourceDefinition]:
    rows: List[Dict] = await read_csv_file(file_path=file_path)
    resource_definitions = []
    
    for row in rows:
        cleaned_row = clean_csv_row(row)
        # Let Pydantic handle validation and defaults
        resource_def = ResourceDefinition.model_validate(cleaned_row)
        resource_definitions.append(resource_def)
    
    return resource_definitions


async def read_item_type_definitions_file(file_path: str) -> List[ItemTypeDefinition]:
    rows: List[Dict] = await read_csv_file(file_path=file_path)
    item_type_definitions = []
    
    for row in rows:
        cleaned_row = clean_csv_row(row)
        # Let Pydantic handle validation and defaults
        item_type_def = ItemTypeDefinition.model_validate(cleaned_row)
        item_type_definitions.append(item_type_def)
    
    return item_type_definitions


async def read_skills_file(file_path: str) -> List[Skill]:
    rows: List[Dict] = await read_csv_file(file_path=file_path)
    skills = []
    
    for row in rows:
        cleaned_row = clean_csv_row(row)
        
        # Parse modifies_attributes field if present
        if cleaned_row.get('modifies_attributes'):
            modifies_attributes_raw = list(filter(None, cleaned_row['modifies_attributes'].split(';')))
            modifies_attributes = []
            for entry in modifies_attributes_raw:
                entry_splits = list(filter(None, entry.split(':')))
                if len(entry_splits) >= 2:
                    modifies_attributes.append({
                        'att_name': entry_splits[0],
                        'modification': int(entry_splits[1])
                    })
            cleaned_row['modifies_attributes'] = modifies_attributes
        
        # Let Pydantic handle validation and defaults
        skill = Skill.model_validate(cleaned_row)
        skills.append(skill)
    
    return skills


async def read_status_modifiers_file(file_path: str) -> List[StatusModifier]:
    rows: List[Dict] = await read_csv_file(file_path=file_path)
    status_modifiers = []
    
    for row in rows:
        cleaned_row = clean_csv_row(row)
        
        # Parse modifies_attributes field if present
        if cleaned_row.get('modifies_attributes'):
            modifies_attributes_raw = list(filter(None, cleaned_row['modifies_attributes'].split(';')))
            modifies_attributes = []
            for entry in modifies_attributes_raw:
                entry_splits = list(filter(None, entry.split(':')))
                if len(entry_splits) >= 2:
                    modifies_attributes.append({
                        'att_name': entry_splits[0],
                        'modification': int(entry_splits[1])
                    })
            cleaned_row['modifies_attributes'] = modifies_attributes
        
        # Let Pydantic handle validation and defaults
        status_modifier = StatusModifier.model_validate(cleaned_row)
        status_modifiers.append(status_modifier)
    
    return status_modifiers


async def read_actions_file(file_path: str) -> List[Action]:
    rows: List[Dict] = await read_csv_file(file_path=file_path)
    actions = []
    
    for row in rows:
        cleaned_row = clean_csv_row(row)
        
        # Parse action_costs field if present
        if cleaned_row.get('action_costs'):
            action_costs_raw = list(filter(None, cleaned_row['action_costs'].split(';')))
            action_costs = []
            for entry in action_costs_raw:
                entry_splits = list(filter(None, entry.split(':')))
                if len(entry_splits) >= 2:
                    action_costs.append({
                        'res_name': entry_splits[0],
                        'amount': int(entry_splits[1])
                    })
            cleaned_row['action_costs'] = action_costs
        
        # Parse action_classes field if present
        if cleaned_row.get('action_classes'):
            cleaned_row['action_classes'] = list(filter(None, cleaned_row['action_classes'].split(';')))
        
        # Let Pydantic handle validation and defaults
        action = Action.model_validate(cleaned_row)
        actions.append(action)
    
    return actions


async def read_items_file(file_path: str, game_actions: Dict[str, Action] = None) -> List[Item]:
    if game_actions is None:
        game_actions = {}
    
    rows: List[Dict] = await read_csv_file(file_path=file_path)
    items = []
    
    for row in rows:
        cleaned_row = clean_csv_row(row)
        
        # Map CSV field names to model field names
        if cleaned_row.get('item_desc'):
            cleaned_row['item_descr'] = cleaned_row.pop('item_desc')
        
        # Handle item action lookup if action_name is provided
        item_action = None
        if cleaned_row.get('action_name') and cleaned_row['action_name'] in game_actions:
            item_action = game_actions[cleaned_row['action_name']]
        cleaned_row['item_action'] = item_action
        
        # Remove action_name from cleaned_row as it's not part of the Item model
        cleaned_row.pop('action_name', None)
        
        # Let Pydantic handle validation and defaults
        item = Item.model_validate(cleaned_row)
        items.append(item)
    
    return items


async def read_csv_file(file_path: str) -> List[Dict]:
    rows: List[Dict] = []
    with open(file_path, newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)

        for row in map(dict, reader):
            rows.append(row)

    return rows


def clean_csv_row(row: Dict[str, str]) -> Dict[str, any]:
    """
    Preprocesses CSV row data for Pydantic model validation.
    Converts empty strings to None and handles basic type conversions.
    """
    cleaned = {}
    for key, value in row.items():
        # Convert empty strings to None for optional fields
        if value == "" or value is None:
            cleaned[key] = None
        # Handle boolean strings
        elif value == "True":
            cleaned[key] = True
        elif value == "False":
            cleaned[key] = False
        else:
            cleaned[key] = value
    return cleaned
