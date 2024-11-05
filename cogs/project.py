import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, Optional, List
from cogs.dashboard import DashboardCog
from core.cog import Cog
from actions.project import ProjectActions
from mappers.aws_credentials_manager import AWSCredentialsManager

class ProjectCog(Cog):
    project_id: int = -1

    project: Dict[str, str | int] = {
        "id": "",
        "name": "",
        "group_name": "",
        "repository_url": "",
        "channel_id": "",
        "group_id": "",
        "thread_id": ""
    }

    def __init__(self, bot):
        super().__init__(bot, loggerTag='project_config')
        self.project_manager = ProjectActions(bot.guilds[0])
        self.aws_credentials_manager = AWSCredentialsManager()
        self.dashboardCog = DashboardCog(bot)

    async def environment_autocomplete(self, 
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        environments = ['dev', 'qa', 'staging', 'prod']
        return [
            app_commands.Choice(name=env, value=env)
            for env in environments
            if current.lower() in env.lower()
        ]

    async def aws_profile_autocomplete(self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        profiles = self.aws_credentials_manager.list_profiles()
        return [
            app_commands.Choice(name=profile, value=profile)
            for profile in profiles
            if current.lower() in profile.lower()
        ]

    async def process_aws_credentials(self, 
                                    interaction: discord.Interaction, 
                                    aws_profile: Optional[str] = None,
                                    aws_access_key: Optional[str] = None,
                                    aws_secret_key: Optional[str] = None,
                                    aws_region: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Process and validate AWS credentials from either profile or custom credentials"""
        try:
            if aws_profile:
                credentials = self.aws_credentials_manager.get_profile_credentials(aws_profile)
                source = f"profile '{aws_profile}'"
            else:
                if not all([aws_access_key, aws_secret_key, aws_region]):
                    await interaction.followup.send(
                        "When not using a profile, you must provide access key, secret key, and region.",
                        ephemeral=True
                    )
                    return None
                
                credentials = {
                    'aws_access_key': aws_access_key,
                    'aws_secret_key': aws_secret_key,
                    'aws_region': aws_region
                }
                source = "custom credentials"

            is_valid, message = self.aws_credentials_manager.validate_credentials(credentials)
            if not is_valid:
                await interaction.followup.send(
                    f"Invalid AWS credentials from {source}: {message}",
                    ephemeral=True
                )
                return None

            return credentials

        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return None
        except Exception as e:
            await interaction.followup.send(f"Error processing AWS credentials: {str(e)}", ephemeral=True)
            return None

    async def set_project(self, id: int, project_name: str = None, project_group: str = None):
        self.project_id = id
        self.project = await self.project_manager.load(id)
        
        if not self.project:
            raise ValueError(f"Project with ID {id} does not exist. Please configure the project first.")
        return self.project

    @app_commands.command(name="register_project", description="Register a new project with AWS configuration")
    @app_commands.describe(
        project_id="Project ID",
        environment="Environment (dev/qa/staging/prod)",
        name="Custom project name",
        group="Custom project group name",
        profile="AWS profile name",
        key="AWS access key",
        secret="AWS secret key",
        region="AWS region"
    )
    @app_commands.autocomplete(
        environment=environment_autocomplete,
        profile=aws_profile_autocomplete
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def register_project(
        self,
        interaction: discord.Interaction,
        project_id: int,
        environment: str,
        name: Optional[str] = None,
        group: Optional[str] = None,
        profile: Optional[str] = None,
        key: Optional[str] = None,
        secret: Optional[str] = None,
        region: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            await self.set_project(project_id)
            await self._configure_project(interaction, name or self.project["name"], group or self.project["group_name"])
            
            credentials = await self.process_aws_credentials(
                interaction,
                aws_profile=profile,
                aws_access_key=key,
                aws_secret_key=secret,
                aws_region=region
            )
            
            if credentials:
                await self.project_manager.add_aws_environment(
                    project_id=project_id,
                    environment=environment,
                    **credentials
                )
                
                await self.dashboardCog.register_dashboard(interaction, project_id)
                
                await interaction.followup.send(
                    f"Project {project_id} registered successfully with AWS configuration.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Failed to process AWS credentials.",
                    ephemeral=True
                )

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="configure_project", description="Configure a new project or update an existing one")
    @app_commands.describe(
        project_id="Project ID",
        name="Custom project name",
        group="Custom project group name"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def configure_project(
        self,
        interaction: discord.Interaction,
        project_id: int,
        name: Optional[str] = None,
        group: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)
        
        try:
            await self.set_project(project_id)
            await self._configure_project(
                interaction,
                name or self.project["name"],
                group or self.project["group_name"].upper()
            )
        except Exception as e:
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

    async def _configure_project(self, interaction: discord.Interaction, project_name: str, project_group: str):
        try:
            await self.project_manager.add(self.project_id, project_name, project_group)
            await interaction.followup.send(
                f"Project {project_name} (ID: {self.project_id}) has been configured successfully in group {project_group}.",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Error configuring project: {str(e)}")
            raise

    @app_commands.command(name="list_projects", description="List all configured projects")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_projects(self, interaction: discord.Interaction):
        try:
            projects = await self.project_manager.get_projects()
            if not projects:
                await interaction.response.send_message(
                    "No projects have been configured yet.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Configured Projects",
                color=discord.Color.blue()
            )
            
            for project in projects:
                project_id, name, group, _ = project
                embed.add_field(
                    name=f"{name} (ID: {project_id})",
                    value=f"Group: {group}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error listing projects: {str(e)}")
            await interaction.response.send_message(
                f"An error occurred while listing projects: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="remove_project", description="Remove a configured project")
    @app_commands.describe(project_id="ID of the project to remove")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_project(self, interaction: discord.Interaction, project_id: int):
        await interaction.response.defer(ephemeral=True)
        
        try:
            await self.project_manager.remove_project(project_id)
            await interaction.followup.send(
                f"Project with ID {project_id} has been removed successfully.",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Error removing project: {str(e)}")
            await interaction.followup.send(
                f"An error occurred while removing the project: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="configure_aws", description="Configure AWS credentials for a project")
    @app_commands.describe(
        project_id="Project ID",
        environment="Environment (dev/qa/staging/prod)",
        profile="AWS profile name (optional)",
        key="AWS access key (if not using profile)",
        secret="AWS secret key (if not using profile)",
        region="AWS region (if not using profile)"
    )
    @app_commands.autocomplete(
        environment=environment_autocomplete,
        profile=aws_profile_autocomplete
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def configure_aws_project(
        self,
        interaction: discord.Interaction,
        project_id: int,
        environment: str,
        profile: Optional[str] = None,
        key: Optional[str] = None,
        secret: Optional[str] = None,
        region: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)
        
        try:
            await self.set_project(project_id)
            
            credentials = await self.process_aws_credentials(
                interaction,
                aws_profile=profile,
                aws_access_key=key,
                aws_secret_key=secret,
                aws_region=region
            )
            
            if not credentials:
                return

            await self.project_manager.add_aws_environment(
                project_id=project_id,
                environment=environment,
                **credentials
            )

            credential_source = "profile" if profile else "custom credentials"
            await interaction.followup.send(
                f"AWS configuration for project {project_id} has been set successfully for the "
                f"{environment} environment using {credential_source} (region: {credentials['aws_region']})",
                ephemeral=True
            )

        except Exception as e:
            self.logger.error(f"Error configuring AWS project: {str(e)}")
            await interaction.followup.send(
                f"An error occurred while configuring the AWS project: {str(e)}",
                ephemeral=True
            )

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
    cog = ProjectCog(bot)
    await bot.add_cog(cog)
    await bot.tree.sync()