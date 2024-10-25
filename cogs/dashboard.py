from datetime import datetime, timedelta, timezone
import discord
from discord.ext import commands
import asyncio
from configs.constants import DASHBOARD_CHANNEL_NAME
from core.aws_resource_manager import AWSResourceManager
from core.cog import Cog
from core.db.aws_project import AWSProject
from core.db.project import Project, projectFromCursor
from core.discord import Discord
from helpers.datetime import format_date
from helpers.gitlab import GitlabClient
from mocks.gitlab import gitlab_mock
from core.emoji import status_emoji
from jinja2 import Template
from PIL import Image
from io import BytesIO
import aiohttp
from playwright.async_api import async_playwright
import os
import pytz

# Update the paths to use the project root directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

overviewPath = os.path.join(project_root, 'templates', 'overview.html')
projectItemPath = os.path.join(project_root, 'templates', 'partials', 'project-info.html')

class DashboardView(discord.ui.View):
    def __init__(self, project_name: str, project_url: str):
        super().__init__(timeout=None)
        self.project_name = project_name
        self.project_url = project_url

    @discord.ui.button(label="Iniciar novo deploy", style=discord.ButtonStyle.green, custom_id="deploy", emoji="🚀")
    async def deploy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.url = f'{self.project_url}/-/pipelines/new' 
        await interaction.response.send_message(f"Pronto!", ephemeral=True)

    @discord.ui.button(label="Ver no GitLab", style=discord.ButtonStyle.blurple, custom_id="gitlab", emoji="🔗")
    async def gitlab_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.url = self.project_url
        await interaction.response.send_message(f"Pronto!", ephemeral=True)

class DashboardCog(Cog): 
    def __init__(self, bot):
        super().__init__(bot, loggerTag='dashboard')
        self.dashboard_posts = {}
        self.bot.loop.create_task(self.update_dashboards_periodically())
        self.discord = Discord(bot.guilds[0])

    async def getProject(self, project_id: int=None):
        _ = Project()
        cursor = await _.get_project(project_id)
        if cursor:
            self.project = projectFromCursor(cursor)
        else:
            raise Exception(f"Project with ID {project_id} not found.")
            return

        return self.project

    @commands.command(name="create_dashboard", description="Creates or updates a dashboard in the specified forum channel")
    async def create_dashboard(self, ctx, *, project_id: int):
        return await self.register_dashboard(ctx, project_id)

    async def register_dashboard(self, ctx, project_id: int):
        forum_channel = discord.utils.get(ctx.guild.forums, name=DASHBOARD_CHANNEL_NAME)
        
        await self.getProject(project_id)
        
        project_name = self.project.name
        
        if not forum_channel:
            await ctx.send(f"No '{DASHBOARD_CHANNEL_NAME}' forum channel found. Creating for u...")
            await ctx.guild.create_forum(
                name=DASHBOARD_CHANNEL_NAME,
                reason="Dashboard forum channel creation"
            )

        try:
            dashboard_image = await self.generate_dashboard_image()
        except FileNotFoundError:
            await ctx.send("Error: Template files not found. Please check the file paths.")
            return

        view = DashboardView(self.category.name.upper(), self.project.repository_url)

        # Check if a thread with the same name already exists
        existing_thread = discord.utils.get(forum_channel.threads, name=self.category.name.upper())

        if existing_thread:
            try:
                initial_message = await existing_thread.fetch_message(existing_thread.id)
                await initial_message.edit(content="", attachments=[dashboard_image], view=view)
                await ctx.send(f"Dashboard for {self.category.name.upper()} updated.", delete_after=5)
            except discord.NotFound:
                await self.create_new_post(ctx, forum_channel, self.category.name.upper(), dashboard_image, view)
        else:
            await self.create_new_post(ctx, forum_channel, self.category.name.upper(), dashboard_image, view)

        await ctx.send(f"Dashboard for {project_name} created in the 'project-dashboards' forum channel.", delete_after=5)
        


    def get_environment_by_branch(self, branch: str):
        if branch.startswith('develop'):
            return 'dev'
        elif branch.startswith('release'):
            return 'qa'
        elif branch.startswith('master'):
            return 'stag'
        elif branch.startswith('main'):
            return 'stag'
        else:
            return 'prod'

    async def generate_dashboard_image(self):
        gl = await GitlabClient.create()
        # gitlab_project = gl.instance.projects.get(project_id)
        project = self.project

        apm = AWSProject()
        pm = Project()

        grouped_projects = await pm.get_projects_by_group_id(project.group_id)


        with open(projectItemPath, 'r') as f:
            project_info_template = Template(f.read())

        project_last_run = None
        # project_last_run_env = ''
        project_info_html = ''
        self.category = await self.discord.getCategory(int(project.group_id))

        for gp in grouped_projects:

            repository_name = gp.name

            try:
                default_branch = gl.get_default_branch(gp.id)
                print(f"Default branch: {default_branch}")  # Will print 'main' or 'master' etc.
            except Exception as e:
                default_branch = 'main'
                print(f"Error: {e}")

            last_pipeline = gl.get_last_pipeline(gp.id, ref=default_branch)
            if last_pipeline:
                last_run = last_pipeline.updated_at
                
                if project_last_run is None or project_last_run == "Nunca executado!" or last_run > project_last_run:
                    project_last_run = last_run
                
                environments_row = f"{status_emoji[last_pipeline.status]} ({default_branch})"

            elif project_last_run is None:
                project_last_run = "Nunca executado!"
                environments_row=''

            project_info_html += project_info_template.render(
                repository_name=repository_name,
                pipelines_status=environments_row
            )


        # Recovery on AWS a RDS Resource use and Instances API/APP length 
        aws_project = await apm.get_aws_project(project.id, 'prod') or (await apm.get_aws_projects(project_id=project.id))[0] 
        if aws_project:
            aws_manager = AWSResourceManager(aws_project.aws_access_key, aws_project.aws_secret_key, aws_project.aws_region)

        rds_info = aws_manager.get_rds_info() if aws_project else None
        rds_health_score = rds_info['averages']['health'] if rds_info else 0
        ecs_info = aws_manager.get_ecs_info() if aws_project else None
        instances_count = len(ecs_info) if ecs_info else 0
        
        # Load and render the HTML templates
        with open(overviewPath, 'r') as f:
            overview_template = Template(f.read())

        sp_timezone = pytz.timezone('America/Sao_Paulo')
        utc_now = datetime.now(timezone.utc)
        now = utc_now.astimezone(sp_timezone) + timedelta(hours=3)

        overview_html = overview_template.render(
            project_icon="🚀", 
            project_name=self.category.name,
            # updated_at=f'{format_date(project_last_run.strftime("%Y-%m-%d %H:%M:%SZ"))} [{project_last_run_env}]',
            updated_at=format_date(now.strftime("%Y-%m-%d %H:%M:%SZ")),
            humanized_updated_at=format_date(now.strftime("%Y-%m-%d %H:%M:%SZ"), True),
            repositories_box_content=project_info_html,
            progress_bar_value=rds_health_score,
            resource_use=f'{rds_health_score:.2f}%',
            instances_count=instances_count
        )

        # Use Playwright to render HTML and capture screenshot
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(overview_html)
            await page.set_viewport_size({"width": 500, "height": 300})
            screenshot = await page.screenshot()
            await browser.close()

        return discord.File(BytesIO(screenshot), filename="dashboard.png")

    async def create_new_post(self, ctx, forum_channel, project_name, dashboard_image, view):
        thread = await forum_channel.create_thread(
            name=project_name,
            content="",
            file=dashboard_image,
            view=view
        )
        if not thread:
            ctx.send(f"Failed to create thread for project: {project_name}")
            return
        self.dashboard_posts[project_name] = thread.id

    async def update_dashboards_periodically(self):
        print("Update Dashboard Task Started")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            print("Update Dashboard Task: Updating dashboards...")
            guild = self.bot.guilds[0]
            for category in guild.categories:
                for project in await Project().get_projects_by_group_id(category.id):
                    forum_channel = discord.utils.get(guild.forums, name=DASHBOARD_CHANNEL_NAME)
                    if forum_channel:
                        try:
                            await self.getProject(project.id)
                            thread_name = self.project.group_name.upper()
                            
                            view = DashboardView(thread_name)
                            dashboard_image = await self.generate_dashboard_image()

                            # Check if a thread with the same name already exists
                            existing_thread = discord.utils.get(forum_channel.threads, name=thread_name)

                            if existing_thread:
                                try:
                                    initial_message = await existing_thread.fetch_message(existing_thread.id)
                                    await initial_message.edit(content="", attachments=[dashboard_image], view=view)
                                except discord.NotFound:
                                    # Modified this part to not use ctx
                                    thread = await forum_channel.create_thread(
                                        name=thread_name,
                                        content="",
                                        file=dashboard_image,
                                        view=view
                                    )
                                    self.dashboard_posts[thread_name] = thread.id

                        except discord.NotFound:
                            print(f"Dashboard thread for {thread_name} not found. Removing from tracking.")
                            if thread_name in self.dashboard_posts:
                                del self.dashboard_posts[thread_name]
                        except Exception as e:
                            print(f"Error updating dashboard for {thread_name}: {str(e)}")
            
            print("Update Dashboard Task: Dashboards updated.")
            await asyncio.sleep(60 * 3)  # Update every 3 minute

async def setup(bot):
    await bot.add_cog(DashboardCog(bot))