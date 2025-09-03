#! logging_manager.py
# a class for managing bot_logging across modules

import os
import logging
import discord
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv

load_dotenv()
BASE_PATH = os.getenv('BASE_PATH')

def create_logger(path):
    created_logger = logging.getLogger('wolfbot_logger')

    file_path = os.path.join(path, "wolfbot_log.txt")

    handler = TimedRotatingFileHandler(file_path,
                                       when="d",
                                       interval=1,
                                       backupCount=15)
    fmt = '[%(asctime)s] [%(levelname)s] - %(message)s'
    formatter = logging.Formatter(fmt=fmt, datefmt='%Y%m%d %H:%M:%S')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)

    created_logger.addHandler(handler)
    created_logger.addHandler(console)
    created_logger.setLevel(logging.INFO)

    return created_logger

def log_interaction_call(interaction: discord.Interaction):
    logger.info(f'Received command {interaction.command.name} with parameters {interaction.data} initiated by user {interaction.user.name}')

def log_info(msg: str):
    logger.info(msg)

def log_warning(msg: str):
    logger.warning(msg)

def log_error(msg: str):
    logger.error(msg)

logger = create_logger(BASE_PATH)
