from typing import Dict, Optional
import discord
from discord.ext import commands
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


    async def process_aws_credentials(self, ctx, 
                                    aws_profile: Optional[str] = None,
                                    aws_access_key: Optional[str] = None,
                                    aws_secret_key: Optional[str] = None,
                                    aws_region: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Process and validate AWS credentials from either profile or custom credentials"""
        try:
            if aws_profile:
                # Using profile
                credentials = self.aws_credentials_manager.get_profile_credentials(aws_profile)
                source = f"profile '{aws_profile}'"
            else:
                # Using custom credentials
                if not all([aws_access_key, aws_secret_key, aws_region]):
                    await ctx.send("When not using a profile, you must provide access key, secret key, and region.")
                    return None
                
                credentials = {
                    'aws_access_key': aws_access_key,
                    'aws_secret_key': aws_secret_key,
                    'aws_region': aws_region
                }
                source = "custom credentials"

            # Validate credentials
            is_valid, message = self.aws_credentials_manager.validate_credentials(credentials)
            if not is_valid:
                await ctx.send(f"Invalid AWS credentials from {source}: {message}")
                return None

            return credentials

        except ValueError as e:
            await ctx.send(str(e))
            return None
        except Exception as e:
            await ctx.send(f"Error processing AWS credentials: {str(e)}")
            return None


    async def set_project(self, id: int, project_name: str = None, project_group: str = None):
        self.project_id = id
        self.project = await self.project_manager.load(id)
        
        if not self.project:
            await ctx.send(f"Project with ID {id} does not exist. Please configure the project first.")
            return
        return self.project

    @commands.command(name="register-project")
    @commands.has_permissions(administrator=True)
    async def register_project(self, ctx, project_id: int, environment: str, *args):
        """
        Configure AWS credentials for a project using either a profile or custom credentials.
        
        Usage: 
        1. Using AWS Profile:
        !register-project <project_id> <environment> --name <custom-project-name> --group <custom-project-group-name> --profile <aws_profile>
        
        2. Using Custom Credentials:
        !register-project <project_id> <environment> --name <custom-project-name> --group <custom-project-group-name> --key <access_key> --secret <secret_key> --region <region>
        """

        
        # Parse arguments
        args_dict = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--'):
                if i + 1 < len(args):
                    args_dict[args[i][2:]] = args[i + 1]
                    i += 2
                else:
                    await ctx.send(f"Missing value for argument {args[i]}")
                    return
            else:
                i += 1


        await self.set_project(project_id)
            

        if 'name' in args_dict:
            project_name = args_dict['name']
        else:
            project_name = None

        if 'group' in args_dict:
            project_group = args_dict['group']
        else:
            project_group = None

        await self._configure_project(ctx, project_name, project_group)
        await self.configure_aws_project(ctx, environment, *args)

        await self.dashboardCog.register_dashboard(ctx, project_id)

    @commands.command(name="configure-project")
    @commands.has_permissions(administrator=True)
    async def configure_project(self, ctx, project_id: int, project_name: str = None, project_group: str = None):
        """
        Configure a new project or update an existing one.
        Usage: 
            !configure-project <project_id>
            !configure-project <project_id> <custom-project-name> <custom-project-group-name>
        """
        await self.set_project(project_id)

        return self._configure_project(ctx, project_name or self.project.name, self.project.group_name.upper())

    async def _configure_project(self, ctx, project_name: str = None, project_group: str = None):
        project_id = self.project_id
        try:            
            # Create or update the project in your database
            await self.project_manager.add(project_id, project_name, project_group)

            await ctx.send(f"Project {project_name} (ID: {project_id}) has been configured successfully in group {project_group}.")
        except Exception as e:
            self.logger.error(f"Error configuring project: {str(e)}")
            await ctx.send(f"An error occurred while configuring the project: {str(e)}")

    @commands.command(name="configure-aws-project")
    @commands.has_permissions(administrator=True)
    async def configure_aws_project(self, ctx, project_id: int, environment: str, *args):
        """
        Configure AWS credentials for a project using either a profile or custom credentials.
        
        Usage: 
        1. Using AWS Profile:
           !configure-aws-project <project_id> <environment> --profile <aws_profile>
        
        2. Using Custom Credentials:
           !configure-aws-project <project_id> <environment> --key <access_key> --secret <secret_key> --region <region>
        """
        try:
            # Parse arguments
            args_dict = {}
            i = 0
            while i < len(args):
                arg = args[i]
                if arg.startswith('--'):
                    if i + 1 < len(args):
                        args_dict[arg[2:]] = args[i + 1]
                        i += 2
                    else:
                        await ctx.send(f"Missing value for argument {arg}")
                        return
                else:
                    i += 1

            # Check if the project exists
            await self.project_manager.load(project_id)
            project = self.project_manager.project
            if not project:
                await ctx.send(f"Project with ID {project_id} does not exist. Please configure the project first.")
                return

            # Process credentials based on provided arguments
            if 'profile' in args_dict:
                credentials = await self.process_aws_credentials( ctx, aws_profile=args_dict['profile'] )
            else:
                credentials = await self.process_aws_credentials(
                    ctx,
                    aws_access_key=args_dict.get('key'),
                    aws_secret_key=args_dict.get('secret'),
                    aws_region=args_dict.get('region')
                )

            if not credentials:
                return

            # Set the AWS configuration for the project
            await self.project_manager.add_aws_environment(
                project_id=project_id,
                environment=environment,
                aws_access_key=credentials['aws_access_key'],
                aws_secret_key=credentials['aws_secret_key'],
                aws_region=credentials['aws_region']
            )

            # Success message
            credential_source = "profile" if 'profile' in args_dict else "custom credentials"
            await ctx.send(
                f"AWS configuration for project {project_id} has been set successfully for the "
                f"{environment} environment using {credential_source} (region: {credentials['aws_region']})"
            )

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