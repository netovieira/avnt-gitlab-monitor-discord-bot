import discord
from discord.ext import commands
import asyncio
from core.cog import Cog
from helpers.datetime import format_date
from mocks.gitlab import gitlab_mock
from core.emoji import status_emoji
from jinja2 import Template
from PIL import Image
from io import BytesIO
import aiohttp
from playwright.async_api import async_playwright
import os

# Update the paths to use the project root directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

overviewPath = os.path.join(project_root, 'templates', 'overview.html')
projectItemPath = os.path.join(project_root, 'templates', 'partials', 'project-info.html')

class DashboardView(discord.ui.View):
    def __init__(self, project_name):
        super().__init__(timeout=None)
        self.project_name = project_name

    @discord.ui.button(label="Iniciar novo deploy", style=discord.ButtonStyle.green, custom_id="deploy")
    async def deploy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"Deploying {self.project_name}...", ephemeral=True)

    @discord.ui.button(label="Ver no GitLab", style=discord.ButtonStyle.blurple, custom_id="gitlab")
    async def gitlab_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        gitlab_url = f"https://gitlab.com/mock-org/{self.project_name.lower().replace(' ', '-')}"
        await interaction.response.send_message(f"View {self.project_name} in GitLab: {gitlab_url}", ephemeral=True)

class DashboardCog(Cog): 
    def __init__(self, bot):
        super().__init__(bot, loggerTag='dashboard')
        self.dashboard_posts = {}
        self.bot.loop.create_task(self.update_dashboards_periodically())

    @commands.command(name="create_dashboard", description="Creates or updates a dashboard in the specified forum channel")
    async def create_dashboard(self, ctx, *, project_name: str):
        forum_channel = discord.utils.get(ctx.guild.forums, name="project-dashboards")
        
        if not forum_channel:
            await ctx.send("No 'project-dashboards' forum channel found. Please create one first.")
            return

        try:
            dashboard_image = await self.generate_dashboard_image(project_name)
        except FileNotFoundError:
            await ctx.send("Error: Template files not found. Please check the file paths.")
            return

        view = DashboardView(project_name)

        # Check if a thread with the same name already exists
        existing_thread = discord.utils.get(forum_channel.threads, name=project_name.capitalize())

        if existing_thread:
            try:
                initial_message = await existing_thread.fetch_message(existing_thread.id)
                await initial_message.edit(attachments=[dashboard_image], view=view)
                await ctx.send(f"Dashboard for {project_name} updated.", delete_after=5)
            except discord.NotFound:
                await self.create_new_post(ctx, forum_channel, project_name, dashboard_image, view)
        else:
            await self.create_new_post(ctx, forum_channel, project_name, dashboard_image, view)

    async def generate_dashboard_image(self, project_name):
        project_data = gitlab_mock.get_project_data(project_name)
        
        # Load and render the HTML templates
        with open(overviewPath, 'r') as f:
            overview_template = Template(f.read())
        with open(projectItemPath, 'r') as f:
            project_info_template = Template(f.read())

        project_info_html = project_info_template.render(
            project_status=status_emoji[project_data['pipeline_status']],
            project_name=project_name,
            project_version='1.0.0'
        )

        overview_html = overview_template.render(
            project_icon="🚀",  # You can replace this with an actual icon
            project_name=project_name.capitalize(),
            version='1.0.0',
            updated_at=format_date(project_data['last_update'].strftime("%Y-%m-%d %H:%M:%SZ")),
            humanized_updated_at=format_date(project_data['last_update'].strftime("%Y-%m-%d %H:%M:%SZ"), True),
            repositories_box_content=project_info_html,
            resource_use="11%",  # Replace with actual data
            instances_count="5"  # Replace with actual data
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
            name=f"{project_name}".capitalize(),
            content="",
            file=dashboard_image,
            view=view
        )
        self.dashboard_posts[project_name] = thread.id
        await ctx.send(f"Dashboard for {project_name} created in the 'project-dashboards' forum channel.", delete_after=5)

    async def update_dashboards_periodically(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            for project_name, thread_id in self.dashboard_posts.items():
                forum_channel = discord.utils.get(self.bot.get_all_channels(), name="project-dashboards")
                if forum_channel:
                    try:
                        thread = await forum_channel.fetch_thread(thread_id)
                        initial_message = await thread.fetch_message(thread.id)
                        dashboard_image = await self.generate_dashboard_image(project_name)
                        view = DashboardView(project_name)
                        await initial_message.edit(attachments=[dashboard_image], view=view)
                    except discord.NotFound:
                        print(f"Dashboard thread for {project_name} not found. Removing from tracking.")
                        del self.dashboard_posts[project_name]
                    except Exception as e:
                        print(f"Error updating dashboard for {project_name}: {str(e)}")
            await asyncio.sleep(60)  # Update every minute

async def setup(bot):
    await bot.add_cog(DashboardCog(bot))