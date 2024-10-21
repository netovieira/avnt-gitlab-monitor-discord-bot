import discord
from discord.ext import commands
from core.cog import Cog
from actions.project import Project
from core.aws_resource_manager import AWSResourceManager

class ProjectCog(Cog):
    def __init__(self, bot):
        super().__init__(bot, loggerTag='project_config')
        self.project_manager = Project()
        self.aws_project_manager = AWSResourceManager()

    @commands.command(name="configure-project")
    @commands.has_permissions(administrator=True)
    async def configure_project(self, ctx, project_id: int, project_name: str = None, project_group: str = None):
        """
        Configure a new project or update an existing one.
        Usage: 
        !configure-project <project_id>
        !configure-project <project_id> <custom-project-name> <custom-project-group-name>
        """
        try:
            # If project_name and project_group are not provided, fetch them from GitLab
            if not project_name or not project_group:
                # Assuming you have a method to fetch project details from GitLab
                gitlab_project = await self.project_manager.get_gitlab_project(project_id)
                project_name = project_name or gitlab_project['name']
                project_group = project_group or gitlab_project['namespace']['name']

            # Create or update the project in your database
            await self.project_manager.set_project(project_id, project_name, project_group, ctx.channel.id, ctx.guild.id, ctx.channel.id)

            await ctx.send(f"Project {project_name} (ID: {project_id}) has been configured successfully in group {project_group}.")
        except Exception as e:
            self.logger.error(f"Error configuring project: {str(e)}")
            await ctx.send(f"An error occurred while configuring the project: {str(e)}")

    @commands.command(name="configure-aws-project")
    @commands.has_permissions(administrator=True)
    async def configure_aws_project(self, ctx, project_id: int, aws_access_key: str, aws_secret_key: str, aws_region: str, environment: str):
        """
        Configure AWS credentials for a project.
        Usage: !configure-aws-project <project_id> <AWS_ACCESS_KEY> <AWS_SECRET_KEY> <AWS_REGION> <ENVIRONMENT>
        """
        try:
            # First, check if the project exists
            project = await self.project_manager.get_project(project_id)
            if not project:
                await ctx.send(f"Project with ID {project_id} does not exist. Please configure the project first.")
                return

            # Set the AWS configuration for the project
            await self.aws_project_manager.set_aws_project(project_id, aws_access_key, aws_secret_key, aws_region)

            # You might want to store the environment somewhere as well
            # For now, we'll just acknowledge it in the response
            await ctx.send(f"AWS configuration for project {project_id} has been set successfully for the {environment} environment.")
        except Exception as e:
            self.logger.error(f"Error configuring AWS project: {str(e)}")
            await ctx.send(f"An error occurred while configuring the AWS project: {str(e)}")

    @commands.command(name="list-projects")
    @commands.has_permissions(administrator=True)
    async def list_projects(self, ctx):
        """List all configured projects."""
        try:
            projects = await self.project_manager.get_projects()
            if not projects:
                await ctx.send("No projects have been configured yet.")
                return

            embed = discord.Embed(title="Configured Projects", color=discord.Color.blue())
            for project in projects:
                project_id, name, group, _ = project
                embed.add_field(name=f"{name} (ID: {project_id})", value=f"Group: {group}", inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error listing projects: {str(e)}")
            await ctx.send(f"An error occurred while listing projects: {str(e)}")

    @commands.command(name="remove-project")
    @commands.has_permissions(administrator=True)
    async def remove_project(self, ctx, project_id: int):
        """Remove a configured project."""
        try:
            await self.project_manager.remove_project(project_id)
            await self.aws_project_manager.remove_aws_project(project_id)
            await ctx.send(f"Project with ID {project_id} has been removed successfully.")
        except Exception as e:
            self.logger.error(f"Error removing project: {str(e)}")
            await ctx.send(f"An error occurred while removing the project: {str(e)}")

async def setup(bot):
    await bot.add_cog(ProjectCog(bot))