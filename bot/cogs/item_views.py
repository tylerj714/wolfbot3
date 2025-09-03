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

item_pi_view_name = "item_view"


class ItemViewButtons(discord.ui.View):
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
                                          guild: Guild, game: Game, items: list[Item], button: discord.ui.Button):
        formatted_responses: list[str] = await construct_item_display(guild=guild, game=game, items=items)

        item_pi_view = game.get_pi_view(item_pi_view_name)
        channel = await guild.fetch_channel(item_pi_view.channel_id)

        i = 0
        while i < len(item_pi_view.message_ids):
            msg_id = item_pi_view.message_ids[i]
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
        time.sleep(2)
        await interaction.message.edit(content=initial_message_content, view=self)
        await interaction.followup.send("Update complete!")

    @discord.ui.button(label="All Items",
                       style=discord.ButtonStyle.gray,
                       custom_id=f'all_{item_pi_view_name}',
                       disabled=True)
    async def all_items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        initial_message_content = interaction.message.content
        game, guild = await self.base_button_initial_functions(interaction=interaction, button=button)

        game_items: list[Item] = game.items
        sorted_game_items = sorted(game_items, key=lambda e: e.item_name.lower())

        await self.base_button_final_functions(initial_message_content=initial_message_content,
                                               interaction=interaction,
                                               guild=guild,
                                               game=game,
                                               items=sorted_game_items,
                                               button=button)

    @discord.ui.button(label="Standard Items",
                       style=discord.ButtonStyle.gray,
                       custom_id=f'std_{item_pi_view_name}')
    async def standard_items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        initial_message_content = interaction.message.content
        game, guild = await self.base_button_initial_functions(interaction=interaction, button=button)

        game_items: list[Item] = game.items
        filtered_game_items = await filter_util.filter_items_by_criteria(item_list=game_items,
                                                                         item_type="Standard Item")
        sorted_game_items = sorted(filtered_game_items, key=lambda e: e.item_name.lower())

        await self.base_button_final_functions(initial_message_content=initial_message_content,
                                               interaction=interaction,
                                               guild=guild,
                                               game=game,
                                               items=sorted_game_items,
                                               button=button)

    @discord.ui.button(label="Altered Items",
                       style=discord.ButtonStyle.gray,
                       custom_id=f'altered_{item_pi_view_name}')
    async def altered_items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        initial_message_content = interaction.message.content
        game, guild = await self.base_button_initial_functions(interaction=interaction, button=button)

        game_items: list[Item] = game.items
        filtered_game_items = await filter_util.filter_items_by_criteria(item_list=game_items,
                                                                         item_type="Altered Item")
        sorted_game_items = sorted(filtered_game_items, key=lambda e: e.item_name.lower())

        await self.base_button_final_functions(initial_message_content=initial_message_content,
                                               interaction=interaction,
                                               guild=guild,
                                               game=game,
                                               items=sorted_game_items,
                                               button=button)


class ItemPersistentInteractiveView(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="items-generate-persistent-view",
                          description="Creates a persistent view of items that can be filtered using buttons")
    @app_commands.default_permissions(manage_guild=True)
    async def items_generate_persistent_view(self,
                                             interaction: discord.Interaction,
                                             item_view_channel: Optional[discord.TextChannel]):
        log_interaction_call(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        game = await gdm.get_game(file_path=Conf.GAME_PATH)
        guild = interaction.guild

        if item_pi_view_name in [pi_view.view_name for pi_view in game.pi_views]:
            await interaction.followup.send(f'Persistent View with name {item_pi_view_name} already exists! '
                                            f'Please delete this view before attempting to create a new one!',
                                            ephemeral=True)
            return

        if not item_view_channel:
            item_view_channel = interaction.channel

        game_items: list[Item] = game.items
        sorted_game_items = sorted(game_items, key=lambda e: e.item_name.lower())

        formatted_responses = await construct_item_display(guild=guild, game=game, items=sorted_game_items)

        msg_channel_ids = []
        for response in formatted_responses:
            sent_message = await item_view_channel.send(f'{response}')
            msg_channel_ids.append(sent_message.id)

        button_message = await item_view_channel.send("Use the buttons below to filter the action list.",
                                                      view=ItemViewButtons())

        game.pi_views.append(PersistentInteractableView(view_name=item_pi_view_name,
                                                        channel_id=item_view_channel.id,
                                                        message_ids=msg_channel_ids,
                                                        button_msg_id=button_message.id))

        await gdm.write_game(game=game)

        await interaction.followup.send(f'Created persistent view in channel {item_view_channel.name} for Items!')


async def setup(bot: commands.Bot) -> None:
    cog = ItemPersistentInteractiveView(bot)
    await bot.add_cog(cog, guilds=[discord.Object(id=Conf.GUILD_ID)])
    log_info(f'Cog {cog.__class__.__name__} loaded!')
