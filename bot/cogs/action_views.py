import discord
import time
from discord import app_commands
from discord.ext import commands
from bot.model.conf_vars import ConfVars as Conf
import bot.model.data_model as gdm
from bot.model.data_model import PersistentInteractableView
from bot.botlogger.logging_manager import log_interaction_call, log_info
from bot.utils.message_formatter import *
import bot.utils.object_filtering_util as filter_util

action_pi_view_name = "action_view"


class ActionViewButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def base_button_initial_functions(self, interaction: discord.Interaction, button: discord.ui.Button) -> (
            Game, Guild):
        button.disabled = True
        for view_child in self.children:
            if type(view_child) == discord.ui.Button and view_child is not button:
                view_child.disabled = True

        await interaction.message.edit(content="List is currently being updated...", view=self)
        await interaction.response.defer(thinking=True, ephemeral=True)

        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        return game, guild

    async def base_button_final_functions(self, initial_message_content: str, interaction: discord.Interaction,
                                          guild: Guild, game: Game, actions: list[Action],
                                          item_actions: list[(str, Action)], button: discord.ui.Button):
        formatted_responses: list[str] = await construct_action_display(guild=guild,
                                                                        game=game,
                                                                        actions=actions,
                                                                        item_actions=item_actions,
                                                                        from_spellbook=True)

        action_pi_view = game.get_pi_view(action_pi_view_name)
        channel = await guild.fetch_channel(action_pi_view.channel_id)

        i = 0
        while i < len(action_pi_view.message_ids):
            msg_id = action_pi_view.message_ids[i]
            msg = await channel.fetch_message(msg_id)
            time.sleep(1)
            if i < len(formatted_responses):
                await msg.edit(content=formatted_responses[i])
            else:
                await msg.edit(content=".")
            time.sleep(1)
            i += 1

        for view_child in self.children:
            if type(view_child) == discord.ui.Button and view_child is not button:
                view_child.disabled = False
        await interaction.message.edit(content=initial_message_content, view=self)
        await interaction.followup.send("Update complete!")

    @discord.ui.button(label="All Actions",
                       style=discord.ButtonStyle.gray,
                       custom_id=f'all_{action_pi_view_name}',
                       disabled=True)
    async def all_actions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        initial_message_content = interaction.message.content
        game, guild = await self.base_button_initial_functions(interaction=interaction, button=button)

        game_actions: list[Action] = game.actions
        game_item_actions: list[(str, Action)] = game.get_item_actions()
        item_action_names = [item_action_entry[1].action_name for item_action_entry in game_item_actions]
        non_item_game_actions = [action for action in game_actions if action.action_name not in item_action_names]

        sorted_game_item_actions = sorted(game_item_actions, key=lambda e: e[0].lower())
        sorted_non_item_game_actions = sorted(non_item_game_actions, key=lambda e: e.action_name.lower())

        await self.base_button_final_functions(initial_message_content=initial_message_content,
                                               interaction=interaction,
                                               guild=guild,
                                               game=game,
                                               actions=sorted_non_item_game_actions,
                                               item_actions=sorted_game_item_actions,
                                               button=button)

    @discord.ui.button(label="Common Actions",
                       style=discord.ButtonStyle.gray,
                       custom_id=f'common_{action_pi_view_name}')
    async def common_actions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        initial_message_content = interaction.message.content
        game, guild = await self.base_button_initial_functions(interaction=interaction, button=button)

        game_actions: list[Action] = game.actions
        filtered_game_actions = await filter_util.filter_actions_by_criteria(action_list=game_actions,
                                                                             action_class="Common")
        sorted_game_actions = sorted(filtered_game_actions, key=lambda e: e.action_name.lower())

        await self.base_button_final_functions(initial_message_content=initial_message_content,
                                               interaction=interaction,
                                               guild=guild,
                                               game=game,
                                               actions=sorted_game_actions,
                                               item_actions=[],
                                               button=button)

    @discord.ui.button(label="Unique Actions",
                       style=discord.ButtonStyle.gray,
                       custom_id=f'unique_{action_pi_view_name}')
    async def unique_actions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        initial_message_content = interaction.message.content
        game, guild = await self.base_button_initial_functions(interaction=interaction, button=button)

        game_actions: list[Action] = game.actions
        filtered_game_actions = await filter_util.filter_actions_by_criteria(action_list=game_actions,
                                                                             action_class="Unique")
        sorted_game_actions = sorted(filtered_game_actions, key=lambda e: e.action_name.lower())

        await self.base_button_final_functions(initial_message_content=initial_message_content,
                                               interaction=interaction,
                                               guild=guild,
                                               game=game,
                                               actions=sorted_game_actions,
                                               item_actions=[],
                                               button=button)

    @discord.ui.button(label="Item Actions",
                       style=discord.ButtonStyle.gray,
                       custom_id=f'items_{action_pi_view_name}', )
    async def item_actions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        initial_message_content = interaction.message.content
        game, guild = await self.base_button_initial_functions(interaction=interaction, button=button)

        game_item_actions: list[(str, Action)] = game.get_item_actions()
        sorted_game_item_actions = sorted(game_item_actions, key=lambda e: e[0].lower())

        await self.base_button_final_functions(initial_message_content=initial_message_content,
                                               interaction=interaction,
                                               guild=guild,
                                               game=game,
                                               actions=[],
                                               item_actions=sorted_game_item_actions,
                                               button=button)


class ActionPersistentInteractiveView(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="actions-generate-persistent-view",
                          description="Creates a persistent view of actions that can be filtered using buttons")
    @app_commands.default_permissions(manage_guild=True)
    async def actions_generate_persistent_view(self,
                                               interaction: discord.Interaction,
                                               action_view_channel: Optional[discord.TextChannel]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        if action_pi_view_name in [pi_view.view_name for pi_view in game.pi_views]:
            await interaction.followup.send(f'Persistent View with name {action_pi_view_name} already exists! '
                                            f'Please delete this view before attempting to create a new one!',
                                            ephemeral=True)
            return

        if not action_view_channel:
            action_view_channel = interaction.channel

        game_actions: list[Action] = game.actions
        game_item_actions: list[(str, Action)] = game.get_item_actions()
        item_action_names = [item_action_entry[1].action_name for item_action_entry in game_item_actions]
        non_item_game_actions = [action for action in game_actions if action.action_name not in item_action_names]

        sorted_game_item_actions = sorted(game_item_actions, key=lambda e: e[0].lower())
        sorted_non_item_game_actions = sorted(non_item_game_actions, key=lambda e: e.action_name.lower())

        formatted_responses = await construct_action_display(actions=sorted_non_item_game_actions,
                                                             item_actions=sorted_game_item_actions,
                                                             guild=guild,
                                                             game=game)

        msg_channel_ids = []
        for response in formatted_responses:
            sent_message = await action_view_channel.send(f'{response}')
            msg_channel_ids.append(sent_message.id)

        button_message = await action_view_channel.send("Use the buttons below to filter the action list.",
                                                        view=ActionViewButtons())

        game.pi_views.append(PersistentInteractableView(view_name=action_pi_view_name,
                                                        channel_id=action_view_channel.id,
                                                        message_ids=msg_channel_ids,
                                                        button_msg_id=button_message.id))

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Created persistent view in channel {action_view_channel.name} for Actions!')


async def setup(bot: commands.Bot) -> None:
    cog = ActionPersistentInteractiveView(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
