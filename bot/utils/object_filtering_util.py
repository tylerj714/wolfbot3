from typing import Optional
from bot.model.data_model import Action, Item, StatusModifier

async def filter_actions_by_criteria(action_list: list[Action],
                                     action_class: Optional[str] = None,
                                     action_timing: Optional[str] = None,
                                     action_level_req: Optional[int] = None) -> list[Action]:

    filtered_action_list: list[Action] = []

    for action in action_list:
        if action_class and action_class in action.action_classes:
            filtered_action_list.append(action)
        elif action_timing and action_timing == action.action_timing:
            filtered_action_list.append(action)
        elif action_level_req and action_level_req == action.action_level_req:
            filtered_action_list.append(action)
    return filtered_action_list

async def filter_items_by_criteria(item_list: list[Item],
                                   item_type: Optional[str] = None,
                                   item_subtype: Optional[str] = None,
                                   item_rarity: Optional[str] = None,
                                   item_properties: Optional[str] = None) -> list[Item]:
    filtered_item_list: list[Item] = []

    for item in item_list:
        if item_type and item_type in item.item_type:
            filtered_item_list.append(item)
        elif item_subtype and item_subtype == item.item_subtype:
            filtered_item_list.append(item)
        elif item_rarity and item_rarity == item.item_rarity:
            filtered_item_list.append(item)
        elif item_properties and item_properties == item.item_properties:
            filtered_item_list.append(item)
    return filtered_item_list

async def filter_status_modifier_by_criteria(stat_mod_list: list[StatusModifier],
                                             modifier_type: Optional[str] = None) -> list[StatusModifier]:
    filtered_stat_mod_list: list[StatusModifier] = []

    for stat_mod in stat_mod_list:
        if modifier_type and modifier_type in stat_mod.modifier_type:
            filtered_stat_mod_list.append(stat_mod)
    return filtered_stat_mod_list
