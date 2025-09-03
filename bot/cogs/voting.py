#! voting.py
# Class with slash commands managing round and dilemma voting

import discord
from discord import app_commands
from discord import TextChannel, Message, Role
from discord.ext import commands
from bot.model.conf_vars import ConfVars as Conf
import bot.model.data_model as gdm
from typing import Optional, Literal, List
from bot.model.data_model import Game, Round, Dilemma, Player, Vote
from bot.botlogger.logging_manager import log_interaction_call, log_info
from bot.utils.command_autocompletes import player_list_autocomplete, dilemma_choice_autocomplete, dilemma_name_autocomplete
import time


async def create_and_pin_report_message(channel: TextChannel, report_name: str, report_type: str) -> int:
    formatted_message = await construct_vote_report(game=None, report_name=report_name, report_type=report_type,
                                                    votes=[])
    report_message = await channel.send(formatted_message)
    await report_message.pin()
    return report_message.id


async def update_report_message(interaction: discord.Interaction, channel_id: int, message_id: int, report_name: str,
                                report_type: str, game: Game, votes: List[Vote]):
    channel = await interaction.guild.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id)
    formatted_votes = await construct_vote_report(report_name=report_name, report_type=report_type, game=game,
                                                  votes=votes)
    await message.edit(content=formatted_votes)


async def construct_vote_report(report_name: str, report_type: str, game: Optional[Game] = None,
                                votes: List[Vote] = None) -> str:
    if votes is None:
        votes = []

    vote_dict = {}

    formatted_votes = f"**Vote Totals for {report_type}: {report_name} as of <t:{int(time.time())}>**\n"
    formatted_votes += "```\n"

    # Vote list is not empty
    if votes:
        for vote in votes:
            if vote.choice in vote_dict.keys():
                vote_dict.get(vote.choice).append(vote.player_id)
            else:
                vote_dict[vote.choice] = [vote.player_id]

        for key, value in sorted(vote_dict.items(), key=lambda e: len(e[1]), reverse=True):
            game_player: Optional[Player]
            try:
                player_id = int(key)
                game_player = game.get_player(player_id)
            except ValueError:
                game_player = None

            if game_player is None:
                formatted_votee = key
            else:
                formatted_votee = game_player.player_discord_name
            formatted_votes += f"{formatted_votee}: {len(value)} vote(s)\n"
            formatted_votes += f"    Voted By: "
            for player_id in value:
                formatted_voter = game.get_player(int(player_id)).player_discord_name
                formatted_votes += f"{formatted_voter}, "
            formatted_votes = formatted_votes.rstrip(', ')
            formatted_votes += "\n"

    else:
        formatted_votes += f"Much empty. Very not democracy."
    formatted_votes += "```\n"

    return formatted_votes


class VotingManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="round-create",
                          description="Creates and enables the current round, if possible")
    @app_commands.default_permissions(manage_guild=True)
    async def round_create(self,
                           interaction: discord.Interaction,
                           channel: Optional[TextChannel]):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        latest_round = game.get_latest_round()

        report_channel = channel if channel is not None else interaction.guild.get_channel(Conf.VOTE_CHANNEL)

        if latest_round is None:
            message_id = await create_and_pin_report_message(channel=report_channel, report_name="1",
                                                             report_type="Round")
            new_round = Round(votes=[], round_channel_id=report_channel.id, round_message_id=message_id,
                              round_dilemmas=[], round_number=1, is_active_round=True)
            game.add_round(new_round)
        elif latest_round.is_active_round:
            await interaction.response.send_message(
                f'There is already an active round; you must end the existing round first before creating another',
                ephemeral=True)
            return
        else:
            message_id = await create_and_pin_report_message(channel=report_channel,
                                                             report_name=f'{latest_round.round_number + 1}',
                                                             report_type="Round")
            new_round = Round(votes=[], round_channel_id=report_channel.id, round_message_id=message_id,
                              round_dilemmas=[], round_number=latest_round.round_number + 1, is_active_round=True)
            game.add_round(new_round)

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'Created round {new_round.round_number}!', ephemeral=True)

    @app_commands.command(name="round-end",
                          description="Ends the current round, if possible")
    @app_commands.default_permissions(manage_guild=True)
    async def round_end(self,
                        interaction: discord.Interaction):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        latest_round = game.get_latest_round()

        if latest_round is None:
            await interaction.response.send_message(f'There is not currently an active round to end!', ephemeral=True)
            return
        else:
            latest_round.is_active_round = False

        await gdm.write_game(game=game)
        await interaction.response.send_message(f'Ended round {latest_round.round_number}!', ephemeral=True)

    @app_commands.command(name="round-vote",
                          description="Votes for a particular player")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    @app_commands.autocomplete(player=player_list_autocomplete)
    async def round_vote(self, interaction: discord.Interaction,
                         player: Optional[str] = None,
                         other: Optional[Literal['No Vote', 'Unvote']] = None):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        if not game.is_active:
            await interaction.response.send_message(
                f'The bot has been put in an inactive state by the moderator. Please try again later.', ephemeral=True)
            return
        elif game.voting_locked:
            await interaction.response.send_message(f'Voting is currently locked.', ephemeral=True)
            return

        if player is not None and other is not None:
            await interaction.response.send_message(
                f'You may select only one of the arguments player or other, you cannot select both. Please resubmit your vote.',
                ephemeral=True)
            return

        latest_round = game.get_latest_round()
        if latest_round is None or not latest_round.is_active_round:
            await interaction.response.send_message(f'No currently active round found for this game!', ephemeral=True)
            return

        requesting_player = game.get_player(interaction.user.id)
        if requesting_player is None or requesting_player.is_dead:
            await interaction.response.send_message(f'Player {interaction.user.name} was not found in this game!',
                                                    ephemeral=True)
            return

        if player is not None and player not in game.get_living_player_ids():
            await interaction.response.send_message(f'Invalid player selection! Please resubmit your vote.',
                                                    ephemeral=True)
            return

        voted_player = None if player is None else game.get_player(int(player))

        if voted_player is not None and voted_player.is_dead:
            await interaction.response.send_message(
                f'Player {voted_player.player_discord_name} is dead and cannot be voted!', ephemeral=True)
            return

        if voted_player is None and other is None:
            await interaction.response.send_message(f'Player {player.name} was not found in this game!', ephemeral=True)
            return

        round_current_player_vote = latest_round.get_player_vote(requesting_player.player_id)

        if voted_player is None and other is not None:
            if round_current_player_vote is None and other != 'Unvote':
                latest_round.add_vote(Vote(requesting_player.player_id, other, round(time.time())))
            else:
                if other == 'Unvote':
                    latest_round.remove_vote(round_current_player_vote)
                else:
                    round_current_player_vote.choice = other
                    round_current_player_vote.timestamp = round(time.time())
        else:
            if round_current_player_vote is None:
                latest_round.add_vote(
                    Vote(requesting_player.player_id, str(voted_player.player_id), round(time.time())))
            else:
                round_current_player_vote.choice = str(voted_player.player_id)
                round_current_player_vote.timestamp = round(time.time())

        await gdm.write_game(game=game)

        await update_report_message(interaction=interaction, channel_id=latest_round.round_channel_id,
                                    message_id=latest_round.round_message_id,
                                    report_name=f'{latest_round.round_number}',
                                    report_type="Round", game=game, votes=latest_round.votes)

        if voted_player is not None:
            success_vote_target = voted_player.player_discord_name
        else:
            success_vote_target = other
        await interaction.response.send_message(f'Registered vote for {success_vote_target}!', ephemeral=True)

        vote_channel = await interaction.guild.fetch_channel(latest_round.round_channel_id)

        response_value = voted_player.player_discord_name if voted_player is not None else other

        if vote_channel is not None:
            await interaction.followup.send(f'Sending public vote announcement in channel #{vote_channel}',
                                            ephemeral=True)
            await vote_channel.send(
                f'Player **{requesting_player.player_discord_name}** has submitted a vote for **{response_value}**')
        else:
            await interaction.followup.send(f'Sending public vote results now...', ephemeral=True)
            await interaction.followup.send(
                f'Player **{requesting_player.player_discord_name}** has submitted a vote for **{response_value}**',
                ephemeral=False)

    @app_commands.command(name="round-vote-report",
                          description="Generates a report of current voting totals")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    async def round_vote_report(self,
                                interaction: discord.Interaction,
                                for_round: Optional[app_commands.Range[int, 0, 20]] = None):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        if not game.is_active:
            await interaction.response.send_message(
                f'The bot has been put in an inactive state by the moderator. Please try again later.', ephemeral=True)
            return

        if for_round is None:
            report_round = game.get_latest_round()
        else:
            report_round = game.get_round(for_round)

        if report_round is None:
            await interaction.response.send_message(f'No active or matching round found for this game!', ephemeral=True)
            return

        formatted_votes = await construct_vote_report(report_name=f'{report_round.round_number}', report_type="Round",
                                                      game=game, votes=report_round.votes)

        vote_channel = interaction.guild.get_channel(report_round.round_channel_id)

        if vote_channel is not None:
            await interaction.response.send_message(f'Sending query response in channel ', ephemeral=True)
            await vote_channel.send(formatted_votes)
        else:
            await interaction.response.send_message(f'Sending vote results now...', ephemeral=True)
            await interaction.followup.send(formatted_votes, ephemeral=False)
        # TODO: Add history functionality

    @app_commands.command(name="dilemma-create",
                          description="Creates and enables a dilemma for the current round, if possible")
    @app_commands.default_permissions(manage_guild=True)
    async def dilemma_create(self, interaction: discord.Interaction,
                             dilemma_name: str,
                             dilemma_channel: discord.TextChannel):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        latest_round = game.get_latest_round()

        if latest_round is None:
            await interaction.response.send_message(
                f'There is currently no active round; you must create an active round first', ephemeral=True)
            return
        elif not latest_round.is_active_round:
            await interaction.response.send_message(
                f'The most recent round is not currently active; the current round must be active to create a dilemma!',
                ephemeral=True)
            return
        else:
            message_id = await create_and_pin_report_message(channel=dilemma_channel, report_name=dilemma_name,
                                                             report_type="Dilemma")
            new_dilemma = Dilemma(dilemma_votes=[], dilemma_name=dilemma_name, dilemma_channel_id=dilemma_channel.id,
                                  dilemma_message_id=message_id, dilemma_player_ids=[], dilemma_choices=[],
                                  is_active_dilemma=False)
            latest_round.add_dilemma(new_dilemma)

        await gdm.write_game(game=game)
        await interaction.response.send_message(
            f'Created dilemma {new_dilemma.dilemma_name} for round {latest_round.round_number}!', ephemeral=True)

    @app_commands.command(name="dilemma-mass-update-player",
                          description="Adds or removes all players in the selected channel with the optionally selected role")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(dilemma_name=dilemma_name_autocomplete)
    async def dilemma_mass_update_player(self, interaction: discord.Interaction,
                                         dilemma_name: str,
                                         channel: TextChannel,
                                         role: Optional[Role],
                                         player_action: Literal['Add', 'Remove']):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        latest_round = game.get_latest_round()

        if latest_round is None:
            await interaction.response.send_message(
                f'There is currently no active round; you must create an active round first', ephemeral=True)
            return
        elif not latest_round.is_active_round:
            await interaction.response.send_message(
                f'The most recent round is not currently active; the current round must be active to create a dilemma!',
                ephemeral=True)
            return
        else:

            round_dilemma = latest_round.get_dilemma(dilemma_name)

            if round_dilemma is None:
                await interaction.response.send_message(f'No dilemma found with the name {dilemma_name}!')
                return

            channel_members = channel.members

            if player_action == 'Add':
                for member in channel_members:
                    if role in member.roles:
                        game_player = game.get_player(member.id)
                        if game_player is not None:
                            round_dilemma.add_player(game_player)
                await interaction.response.send_message(
                    f'Added all players in {channel.name} with role {role.name} to dilemma {round_dilemma.dilemma_name}!',
                    ephemeral=True)
            else:
                for member in channel_members:
                    if role in member.roles:
                        game_player = game.get_player(member.id)
                        if game_player is not None:
                            round_dilemma.remove_player(game_player)
                    # TODO: Need to handle the situation where a player that is being removed has already voted?
                await interaction.response.send_message(
                    f'Removed all players in {channel.name} with role {role.name} from dilemma {round_dilemma.dilemma_name}!',
                    ephemeral=True)
        await gdm.write_game(game=game)

    @app_commands.command(name="dilemma-update-player",
                          description="Adds or removes a player from a selected dilemma")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(player=player_list_autocomplete)
    @app_commands.autocomplete(dilemma_name=dilemma_name_autocomplete)
    async def dilemma_update_player(self, interaction: discord.Interaction,
                                    dilemma_name: str,
                                    player: str,
                                    player_action: Literal['Add', 'Remove']):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        latest_round = game.get_latest_round()
        game_player = game.get_player(int(player))

        if latest_round is None:
            await interaction.response.send_message(
                f'There is currently no active round; you must create an active round first', ephemeral=True)
            return
        elif not latest_round.is_active_round:
            await interaction.response.send_message(
                f'The most recent round is not currently active; the current round must be active to create a dilemma!',
                ephemeral=True)
            return
        elif game_player is None:
            await interaction.response.send_message(f'Player was not found in the current game!', ephemeral=True)
            return
        else:

            round_dilemma = latest_round.get_dilemma(dilemma_name)

            if round_dilemma is None:
                await interaction.response.send_message(f'No dilemma found with the name {dilemma_name}!')
                return

            if player_action == 'Add':
                round_dilemma.add_player(game_player)
                await interaction.response.send_message(
                    f'Added player {game_player.player_discord_name} to dilemma {round_dilemma.dilemma_name}!',
                    ephemeral=True)
            else:
                round_dilemma.remove_player(game_player)
                # TODO: Need to handle the situation where a player that is being removed has already voted?
                await interaction.response.send_message(
                    f'Removed player {game_player.player_discord_name} from dilemma {round_dilemma.dilemma_name}!',
                    ephemeral=True)
        await gdm.write_game(game=game)

    @app_commands.command(name="dilemma-update-choices",
                          description="Adds or Removes a choice to a selected dilemma")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(dilemma_name=dilemma_name_autocomplete)
    @app_commands.autocomplete(dilemma_choice_remove=dilemma_choice_autocomplete)
    async def dilemma_update_choices(self,
                                     interaction: discord.Interaction,
                                     dilemma_name: str,
                                     dilemma_choice_add: Optional[str],
                                     dilemma_choice_remove: Optional[str]):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        latest_round = game.get_latest_round()

        if latest_round is None:
            await interaction.response.send_message(
                f'There is currently no active round; you must create an active round first', ephemeral=True)
            return
        elif not latest_round.is_active_round:
            await interaction.response.send_message(
                f'The most recent round is not currently active; the current round must be active to create a dilemma!',
                ephemeral=True)
            return
        else:

            round_dilemma = latest_round.get_dilemma(dilemma_name)

            if round_dilemma is None:
                await interaction.response.send_message(f'No dilemma found with the name {dilemma_name}!')
                return

            if dilemma_choice_add is not None:
                round_dilemma.add_choice(dilemma_choice_add)
                await interaction.response.send_message(
                    f'Added choice {dilemma_choice_add} to dilemma {round_dilemma.dilemma_name}!',
                    ephemeral=True)
            else:
                round_dilemma.remove_choice(dilemma_choice_remove)
                # TODO: Need to handle the situation where a choice that is being removed has already been voted for?
                await interaction.response.send_message(
                    f'Removed choice {dilemma_choice_remove} from dilemma {round_dilemma.dilemma_name}!',
                    ephemeral=True)
        await gdm.write_game(game=game)

    @app_commands.command(name="dilemma-vote",
                          description="Votes for a particular dilemma choice")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    @app_commands.autocomplete(dilemma_name=dilemma_name_autocomplete)
    @app_commands.autocomplete(dilemma_choice=dilemma_choice_autocomplete)
    async def dilemma_vote(self, interaction: discord.Interaction,
                           dilemma_name: str,
                           dilemma_choice: Optional[str] = None,
                           other_choices: Optional[Literal['Unvote']] = None):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        if not game.is_active:
            await interaction.response.send_message(
                f'The bot has been put in an inactive state by the moderator. Please try again later.', ephemeral=True)
            return
        elif game.voting_locked:
            await interaction.response.send_message(f'Voting is currently locked.', ephemeral=True)
            return

        latest_round = game.get_latest_round()
        if latest_round is None or not latest_round.is_active_round:
            await interaction.response.send_message(f'No currently active round found for this game!', ephemeral=True)
            return

        requesting_player = game.get_player(interaction.user.id)
        if requesting_player is None or requesting_player.is_dead:
            await interaction.response.send_message(f'Player {interaction.user.name} was not found in this game!',
                                                    ephemeral=True)
            return

        player_dilemma = latest_round.get_dilemma(dilemma_name)

        if player_dilemma is None:
            await interaction.response.send_message(
                f'Could not find an active dilemma for player {requesting_player.player_discord_name}!',
                ephemeral=True)
            return

        if dilemma_choice is None and other_choices is None:
            await interaction.response.send_message(
                f'You must select either a dilemma choice or an other choice option!',
                ephemeral=True)
            return

        if dilemma_choice is not None and dilemma_choice not in player_dilemma.dilemma_choices:
            await interaction.response.send_message(
                f'The choice {dilemma_choice} is not a valid selection for your current dilemma!')
            return

        dilemma_current_player_vote = player_dilemma.get_player_vote(requesting_player.player_id)

        if dilemma_current_player_vote is None and dilemma_choice is not None:
            player_dilemma.add_vote(Vote(requesting_player.player_id, dilemma_choice, round(time.time())))
        elif dilemma_current_player_vote is not None and other_choices == 'Unvote':
            player_dilemma.remove_vote(dilemma_current_player_vote)
            dilemma_choice = 'Unvote'
        else:
            dilemma_current_player_vote.choice = dilemma_choice
            dilemma_current_player_vote.timestamp = round(time.time())

        await gdm.write_game(game=game)

        await update_report_message(interaction=interaction, channel_id=player_dilemma.dilemma_channel_id,
                                    message_id=player_dilemma.dilemma_message_id,
                                    report_name=f'{player_dilemma.dilemma_name}',
                                    report_type="Dilemma", game=game, votes=player_dilemma.dilemma_votes)

        await interaction.response.send_message(f'Registered vote for {dilemma_choice}!', ephemeral=True)

        dilemma_channel = interaction.guild.get_channel(player_dilemma.dilemma_channel_id)

        if dilemma_channel is not None:
            await interaction.followup.send(f'Sending public vote announcement in channel #{dilemma_channel}',
                                            ephemeral=True)
            await dilemma_channel.send(
                f'Player **{requesting_player.player_discord_name}** has submitted a dilemma vote for **{dilemma_choice}**')
        else:
            await interaction.followup.send(f'Sending public vote results now...', ephemeral=True)
            await interaction.followup.send(
                f'Player **{requesting_player.player_discord_name}** has submitted a dilemma vote for **{dilemma_choice}**',
                ephemeral=False)

    @app_commands.command(name="dilemma-vote-report",
                          description="Generates a report of current voting totals for a player's active dilemma")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id)
    @app_commands.autocomplete(dilemma_name=dilemma_name_autocomplete)
    async def dilemma_vote_report(self,
                                  interaction: discord.Interaction,
                                  dilemma_name: str):
        log_interaction_call(interaction)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)

        if not game.is_active:
            await interaction.response.send_message(
                f'The bot has been put in an inactive state by the moderator. Please try again later.', ephemeral=True)
            return

        report_round = game.get_latest_round()

        if report_round is None:
            await interaction.response.send_message(f'No active or matching dilemma found for this game!',
                                                    ephemeral=True)
            return

        game_player = game.get_player(interaction.user.id)

        if game_player is None or game_player.is_dead:
            await interaction.response.send_message(f'No active player for this game found!', ephemeral=True)
            return

        player_dilemma = report_round.get_dilemma(dilemma_name)

        if player_dilemma is None:
            await interaction.response.send_message(f'No active dilemma found!', ephemeral=True)

        formatted_votes = await construct_vote_report(game=game, report_name=dilemma_name, report_type="Dilemma",
                                                      votes=player_dilemma.dilemma_votes)

        dilemma_channel = interaction.guild.get_channel(player_dilemma.dilemma_channel_id)

        if dilemma_channel is not None:
            await interaction.response.send_message(f'Sending query response in channel ', ephemeral=True)
            await dilemma_channel.send(formatted_votes)
        else:
            await interaction.response.send_message(f'Sending vote results now...', ephemeral=True)
            await interaction.followup.send(formatted_votes, ephemeral=False)


async def setup(bot: commands.Bot) -> None:
    cog = VotingManager(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
