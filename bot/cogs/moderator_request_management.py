#! moderator_request_management.py
# Class with slash commands managing game state

import discord
from discord import app_commands
from discord.ext import commands
from bot.model.conf_vars import ConfVars as Conf
import bot.model.data_model as gdm
from bot.botlogger.logging_manager import log_interaction_call, log_info
from bot.utils.command_autocompletes import player_action_autocomplete, game_action_autocomplete
from bot.utils.message_formatter import *


async def send_message_to_moderator(message: str, guild: Guild):
    mod_request_channel = await guild.fetch_channel(Conf.REQUEST_CHANNEL)

    formatted_request = f'<@&{Conf.MOD_ROLE_ID}>\n'
    formatted_request += f'{message}\n'

    await mod_request_channel.send(formatted_request)


class ModRequestManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mod-request",
                          description="Send a request to the moderator through a private channel")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    async def moderator_request(self, interaction: discord.Interaction,
                                request: str):
        log_interaction_call(interaction)
        game = await gdm.get_game(Conf.GAME_PATH)

        mod_request_channel = await interaction.guild.fetch_channel(Conf.REQUEST_CHANNEL)

        requesting_player = game.get_player(interaction.user.id)

        if requesting_player is None:
            await interaction.response.send_message(
                f'Player {interaction.user.name} is not currently defined in this game!', ephemeral=True)
            return
        elif requesting_player.is_dead:
            await interaction.response.send_message(f'You are dead! Begone apparition!')
            return
        else:
            await interaction.response.send_message(f'Submitted request **{request}** to the moderator!',
                                                    ephemeral=True)
            await mod_request_channel.send(
                f'<@&{Conf.MOD_ROLE_ID}>\nPlayer **{requesting_player.player_discord_name}** has submitted an moderator request of **{request}**\n')

    @app_commands.command(name="action-submission",
                          description="Submit an action to be performed to the moderator")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    @app_commands.describe(target1="Optional - First chosen target for action (free-form text field)")
    @app_commands.rename(target1="first-target")
    @app_commands.describe(target2="Optional - Second chosen target for action (free-form text field)")
    @app_commands.rename(target2="second-target")
    @app_commands.describe(target3="Optional - Third chosen target for action (free-form text field)")
    @app_commands.rename(target3="third-target")
    @app_commands.describe(request_details="Optional - Any additional necessary non-targeting information (free-form text field)")
    @app_commands.rename(request_details="request-details")
    @app_commands.autocomplete(action=player_action_autocomplete)
    async def action_submission(self, interaction: discord.Interaction,
                                action: str,
                                target1: Optional[str],
                                target2: Optional[str],
                                target3: Optional[str],
                                request_details: Optional[str]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(Conf.GAME_PATH)
        guild = interaction.guild

        mod_request_channel = await interaction.guild.fetch_channel(Conf.REQUEST_CHANNEL)

        requesting_player = game.get_player(interaction.user.id)

        if requesting_player is None:
            await interaction.followup.send(
                f'Player {interaction.user.name} is not currently defined in this game!', ephemeral=True)
            return
        elif requesting_player.is_dead:
            await interaction.followup.send(f'You are dead! Begone apparition!', ephemeral=True)
            return
        else:
            # Here is where we deduct uses and pay costs automatically
            player_action = requesting_player.get_action(action_name=action)

            # Actions with -1 uses are unlimited
            if player_action.action_uses != -1:
                # Actions with non -1 value uses have limited uses; players must have remaining uses to submit the action
                if player_action.action_uses > 0:
                    player_action.action_uses = player_action.action_uses - 1
                else:
                    await interaction.followup.send(f'You do not have any remaining uses for this action!',
                                                    ephemeral=True)
                    return

            # Actions with an empty costs list have no associated costs and can be used freely
            if player_action.action_costs:
                for action_cost in player_action.action_costs:
                    player_resource = requesting_player.get_resource(action_cost.res_name)
                    if not player_resource:
                        await interaction.followup.send(f'Could not find resource {action_cost.res_name} for '
                                                        f'player! Please contact the game moderator!')
                        return
                    # First, verify the player can actually pay the costs
                    if player_resource.resource_amt < action_cost.amount:
                        # If costs cannot be paid, reject the action submission with reasoning
                        ins_res_msg = await insufficient_resources_msg(action=player_action,
                                                                       player=requesting_player,
                                                                       game=game,
                                                                       guild=guild)
                        await interaction.followup.send(ins_res_msg)
                        return
                    else:
                        # If costs can be paid, update player resources to the new value
                        player_resource.resource_amt = player_resource.resource_amt - action_cost.amount

            await gdm.write_game(game)

            await interaction.followup.send(f'Submitted request for action **{action}** to the moderator!',
                                            ephemeral=True)

            # Inform the player of their new resource values:
            player_moderator_channel = await guild.fetch_channel(requesting_player.player_mod_channel)
            if player_moderator_channel:
                if player_action.action_costs:
                    formatted_resources = await construct_player_resources_display(player=requesting_player, guild=guild, game=game)

                    for player_resource_display in formatted_resources:
                        await player_moderator_channel.send(player_resource_display)
                #TODO: Send confirmation in mod chat about action submission

            formatted_request = f'<@&{Conf.MOD_ROLE_ID}>\nPlayer **{requesting_player.player_discord_name}** has requested to use the action **{action}**\n'
            if target1:
                formatted_request += f'First Target/Choice: {target1}\n'
            if target2:
                formatted_request += f'Second Target/Choice: {target2}\n'
            if target3:
                formatted_request += f'Third Target/Choice: {target3}\n'
            if request_details:
                formatted_request += f'Additional details: {request_details}\n'

            await mod_request_channel.send(formatted_request)

    @app_commands.command(name="level-up",
                          description="Submit level up requests to the moderator here.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    @app_commands.autocomplete(action=game_action_autocomplete)
    async def level_up(self, interaction: discord.Interaction,
                       action: str,
                       skill: str,
                       attribute1: Literal['Body', 'Mind', 'Spirit'],
                       attribute2: Literal['Body', 'Mind', 'Spirit']):
        log_interaction_call(interaction)
        game = await gdm.get_game(Conf.GAME_PATH)

        mod_request_channel = await interaction.guild.fetch_channel(Conf.REQUEST_CHANNEL)

        requesting_player = game.get_player(interaction.user.id)

        if requesting_player is None:
            await interaction.response.send_message(
                f'Player {interaction.user.name} is not currently defined in this game!', ephemeral=True)
            return
        elif requesting_player.is_dead:
            await interaction.response.send_message(f'You are dead! Begone apparition!', ephemeral=True)
            return
        else:
            await interaction.response.send_message(f'Submitted level up request to the moderator!',
                                                    ephemeral=True)

            formatted_request = f'<@&{Conf.MOD_ROLE_ID}>\nPlayer **{requesting_player.player_discord_name}** has submitted a level-up request:\n'
            formatted_request += f'New Action: {action}\n'
            formatted_request += f'New Skill: {skill}\n'
            formatted_request += f'Attribute 1: {attribute1}\n'
            formatted_request += f'Attribute 2: {attribute2}\n'

            await mod_request_channel.send(formatted_request)


async def setup(bot: commands.Bot) -> None:
    cog = ModRequestManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
