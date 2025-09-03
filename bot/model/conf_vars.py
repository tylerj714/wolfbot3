#! conf_vars.py
# Loads and stores environment variables

import os
from dotenv import load_dotenv

load_dotenv()

class ConfVars:
    # Required Configs
    TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD_ID = int(os.getenv('GUILD_ID'))
    BASE_PATH = os.getenv('BASE_PATH')
    GAME_FILE = os.getenv('GAME_FILE')
    GAME_PATH = f'{BASE_PATH}/{GAME_FILE}'

    # Optional Arguments - Some Commands Require These Commands if used
    MOD_ROLE_ID = int(os.getenv('MOD_ROLE_ID'))
    PRIVATE_CHAT_CATEGORY = int(os.getenv('PRIVATE_CHAT_CATEGORY'))
    MOD_CATEGORY = int(os.getenv('MOD_CATEGORY'))
    REQUEST_CHANNEL = int(os.getenv('REQUEST_CHANNEL'))
    VOTE_CHANNEL = int(os.getenv('VOTE_CHANNEL'))

    # Optional Arguments - Enable advanced functionality
    PLAYER_FILE = os.getenv('PLAYER_FILE')
    PLAYER_PATH = f'{BASE_PATH}/{PLAYER_FILE}' if PLAYER_FILE else None
    PARTY_FILE = os.getenv('PARTY_FILE')
    PARTY_PATH = f'{BASE_PATH}/{PARTY_FILE}' if PARTY_FILE else None
    ATTRIBUTE_DEF_FILE = os.getenv('ATTRIBUTE_DEF_FILE')
    ATTRIBUTE_DEF_PATH = f'{BASE_PATH}/{ATTRIBUTE_DEF_FILE}' if ATTRIBUTE_DEF_FILE else None
    RESOURCE_DEF_FILE = os.getenv('RESOURCE_DEF_FILE')
    RESOURCE_DEF_PATH = f'{BASE_PATH}/{RESOURCE_DEF_FILE}' if RESOURCE_DEF_FILE else None
    ITEM_TYPE_DEF_FILE = os.getenv('ITEM_TYPE_DEF_FILE')
    ITEM_TYPE_DEF_PATH = f'{BASE_PATH}/{ITEM_TYPE_DEF_FILE}' if ITEM_TYPE_DEF_FILE else None
    SKILL_FILE = os.getenv('SKILL_FILE')
    SKILL_PATH = f'{BASE_PATH}/{SKILL_FILE}' if SKILL_FILE else None
    STATUS_MOD_FILE = os.getenv('STATUS_MOD_FILE')
    STATUS_MOD_PATH = f'{BASE_PATH}/{STATUS_MOD_FILE}' if STATUS_MOD_FILE else None
    ACTION_FILE = os.getenv('ACTION_FILE')
    ACTION_PATH = f'{BASE_PATH}/{ACTION_FILE}' if ACTION_FILE else None
    ITEM_FILE = os.getenv('ITEM_FILE')
    ITEM_PATH = f'{BASE_PATH}/{ITEM_FILE}' if ITEM_FILE else None
    CHAR_SHEET_FILE = os.getenv('CHAR_SHEET_FILE')
    CHAR_SHEET_PATH = f'{BASE_PATH}/{CHAR_SHEET_FILE}' if CHAR_SHEET_FILE else None

