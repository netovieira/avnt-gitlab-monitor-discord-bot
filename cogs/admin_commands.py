import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Optional
from actions.project import ProjectActions
from core.cogs.commands_cog import CommandsCog
from core.db.gitlab import Gitlab
from core.db.project import Project
from helpers.messages import HELP_MESSAGE_CONTENT

class AdminCommands(CommandsCog):
    def __init__(self, bot):
        super().__init__(bot, loggerTag='admin')
        self.project = Project()
        self.gitlab = Gitlab()
        
    @app_commands.command(name="clear", description="Clear messages from the channel")
    @app_commands.describe(
        amount="Number of messages to delete or 'all' for all messages"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: str):
        if amount.lower() == "all" or amount.lower() == "tudo":
            await interaction.response.defer()
            
            try:
                deleted = 0
                while True:
                    deleted_msgs = await interaction.channel.purge(limit=100)
                    if len(deleted_msgs) < 100:
                        deleted += len(deleted_msgs)
                        break
                    deleted += 100
                    await asyncio.sleep(1)
                
                await interaction.followup.send(f"Cleaned {deleted} messages.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("I don't have permission to delete messages.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
            return

        try:
            amt = int(amount)
            if amt <= 0:
                await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
                return
                
            if amt > 100:
                await interaction.response.send_message("You can only delete up to 100 messages at once.", ephemeral=True)
                return
                
            await interaction.response.defer()
            deleted = await interaction.channel.purge(limit=amt)
            await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("Please provide a valid number.", ephemeral=True)

    @app_commands.command(name="help", description="Show bot help information")
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.send_message(HELP_MESSAGE_CONTENT[0], ephemeral=True)
        for message in HELP_MESSAGE_CONTENT[1:]:
            await interaction.followup.send(message, ephemeral=True)

    @app_commands.command(name="config_gitlab", description="Configure GitLab integration")
    @app_commands.describe(
        url="GitLab instance URL",
        token="GitLab access token"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_gitlab(self, interaction: discord.Interaction, url: str, token: str):
        await interaction.response.defer(ephemeral=True)
        await self.gitlab.set_gitlab_config('url', url)
        await self.gitlab.set_gitlab_config('token', token)
        await interaction.followup.send("GitLab configuration updated successfully!", ephemeral=True)

    async def get_project_suggestions(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[int]]:
        projects = await self.project.get_projects()
        return [
            app_commands.Choice(name=f"{name} ({id})", value=id)
            for id, name, _, _ in projects
            if current.lower() in name.lower() or str(id).startswith(current)
        ][:25]  # Discord limits to 25 choices

    @app_commands.command(name="add_project", description="Add a new project")
    @app_commands.describe(project_id="Project ID to add")
    @app_commands.autocomplete(project_id=get_project_suggestions)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_project(self, interaction: discord.Interaction, project_id: int):
        await interaction.response.defer()
        project = ProjectActions(interaction.guild)
        await project.add(project_id)
        await interaction.followup.send(f"Project {project_id} added successfully!")

    @app_commands.command(name="remove_project", description="Remove a project")
    @app_commands.describe(project_id="Project ID to remove")
    @app_commands.autocomplete(project_id=get_project_suggestions)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_project(self, interaction: discord.Interaction, project_id: int):
        await interaction.response.defer()
        project = ProjectActions(interaction.guild)
        await project.load(project_id)
        await project.remove()
        await interaction.followup.send(f"Project {project_id} removed successfully!")

    @app_commands.command(name="show_config", description="Show current bot configuration")
    @app_commands.checks.has_permissions(administrator=True)
    async def show_config(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        gitlab_url = await self.gitlab.get_gitlab_config('url')
        projects = await self.project.get_projects()

        embed = discord.Embed(
            title="Bot Configuration",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="GitLab URL",
            value=gitlab_url or "Not configured",
            inline=False
        )
        
        projects_text = ""
        for project in projects:
            project_id, project_name, project_group, *_ = project
            projects_text += f"• {project_group.upper()} > {project_name} (ID: {project_id})\n"
            
        if projects_text:
            embed.add_field(
                name="Projects",
                value=projects_text,
                inline=False
            )
        else:
            embed.add_field(
                name="Projects",
                value="No projects configured",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    # Error handlers for slash commands
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"An error occurred: {str(error)}",
                ephemeral=True
            )

async def setup(bot):
    # Register the cog and sync the commands
    cog = AdminCommands(bot)
    await bot.add_cog(cog)
    await bot.tree.sync()  # Sync slash commands with Discord