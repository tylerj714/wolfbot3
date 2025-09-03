#! dice_rolling.py
# Class with slash commands for rolling dice

import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal, Optional
from bot.model.conf_vars import ConfVars as Conf
from bot.botlogger.logging_manager import log_interaction_call, log_info
import random


class DiceManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="roll-dice",
                          description="Rolls dice with a specified number of sides with optional modifier")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    async def roll_dice(self, interaction: discord.Interaction,
                        dice_to_roll: Literal[1, 2, 3, 4, 5],
                        die_faces: Literal[2, 4, 6, 8, 10, 12, 20],
                        with_modifier: Optional[Literal['Advantage', 'Disadvantage']]):
        log_interaction_call(interaction)

        roll_values = []
        roll_values_alt = []

        for x in range(0, dice_to_roll):
            roll_value1: int = random.randint(1, die_faces)
            roll_value2: int = random.randint(1, die_faces)
            if with_modifier is not None:
                if with_modifier == 'Advantage':
                    if roll_value1 >= roll_value2:
                        roll_values.append(roll_value1)
                        roll_values_alt.append(roll_value2)
                    else:
                        roll_values.append(roll_value2)
                        roll_values_alt.append(roll_value1)
                else:
                    if roll_value1 <= roll_value2:
                        roll_values.append(roll_value1)
                        roll_values_alt.append(roll_value2)
                    else:
                        roll_values.append(roll_value2)
                        roll_values_alt.append(roll_value1)
            else:
                roll_values.append(roll_value1)

        roll_values.sort()
        roll_values_alt.sort()

        roll_val_str = ','.join(map(str, roll_values))
        roll_val_alt_str = ','.join(map(str, roll_values_alt))

        roll_message = ""
        result_message = ""
        if with_modifier is not None:
            roll_message += f'Rolling {dice_to_roll} d{die_faces} with {with_modifier}...'
            result_message += f'Rolled values: {roll_val_str}\n'
            result_message += f'Discarded rolled values: ~~{roll_val_alt_str}~~'
        else:
            roll_message += f'Rolling {dice_to_roll} d{die_faces}...'
            result_message += f'Rolled values: {roll_val_str}'

        await interaction.response.send_message(roll_message, ephemeral=False)
        await interaction.followup.send(result_message, ephemeral=False)


async def setup(bot: commands.Bot) -> None:
    cog = DiceManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
