import discord
from discord import app_commands
import asyncio
import pytz
from datetime import datetime, timezone
from configs.constants import DASHBOARD_CHANNEL_NAME
from core.aws_resource_manager import AWSResourceManager
from core.cogs.commands_cog import CommandsCog
from core.db.aws_project import AWSProject
from core.db.project import Project, projectFromCursor
from core.discord import Discord
from helpers.datetime import format_date
from core.emoji import status_emoji
from jinja2 import Template
from io import BytesIO
from playwright.async_api import async_playwright
import os

from helpers.project_auto_complete import project_autocomplete

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

    @discord.ui.button(label="Iniciar novo deploy", style=discord.ButtonStyle.green, custom_id="deploy")
    async def deploy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"Deploying {self.project_name}...", ephemeral=True)

    @discord.ui.button(label="Ver no GitLab", style=discord.ButtonStyle.blurple, custom_id="gitlab")
    async def gitlab_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        gitlab_url = self.project_url
        await interaction.response.send_message(f"View {self.project_name} in GitLab: {gitlab_url}", ephemeral=True)


class DashboardCog(CommandsCog):
    def __init__(self, bot):
        super().__init__(bot, logger_tag='dashboard')
        self.dashboard_posts = {}
        self.discord = None

    async def get_discord(self):
        """Lazy initialization do Discord helper"""
        if self.discord is None:
            if self.bot.guilds:
                self.discord = Discord(self.bot.guilds[0])
            else:
                raise Exception("Bot não conectado a nenhum servidor")
        return self.discord

    async def getProject(self, project_id: int = None):
        _ = Project()
        cursor = await _.get_project(project_id)
        if cursor:
            self.project = projectFromCursor(cursor)
        else:
            raise Exception(f"Project with ID {project_id} not found.")

        return self.project

    def get_ecs_status_emoji(self, service_status):
        """
        Mapeia status do service ECS para emoji
        """
        return status_emoji.get(service_status, status_emoji["failed"])

    def get_timezone_from_aws_region(self, aws_projects):
        """
        Mapeia região AWS para timezone apropriado
        """
        aws_timezone_map = {
            'us-east-1': 'America/New_York',
            'us-east-2': 'America/New_York',
            'us-west-1': 'America/Los_Angeles',
            'us-west-2': 'America/Los_Angeles',
            'sa-east-1': 'America/Sao_Paulo',  # São Paulo
            'eu-west-1': 'Europe/London',
            'eu-west-2': 'Europe/London',
            'eu-central-1': 'Europe/Berlin',
            'ap-southeast-1': 'Asia/Singapore',
            'ap-southeast-2': 'Australia/Sydney',
            'ap-northeast-1': 'Asia/Tokyo',
            # adicionar mais conforme necessário
        }

        # Pegar timezone da primeira região AWS encontrada, default São Paulo
        if aws_projects and len(aws_projects) > 0:
            region = aws_projects[0].aws_region
        else:
            region = 'sa-east-1'

        timezone_name = aws_timezone_map.get(region, 'America/Sao_Paulo')
        return pytz.timezone(timezone_name)

    @app_commands.command(name="create_dashboard",
                          description="Creates or updates a dashboard in the specified forum channel")
    @app_commands.describe(project_id="Selecione o projeto")
    @app_commands.autocomplete(project_id=project_autocomplete)
    async def create_dashboard(self, interaction: discord.Interaction, project_id: int):
        await interaction.response.defer()
        try:
            await self.register_dashboard(interaction, project_id)
        except Exception as e:
            await interaction.followup.send(f"Erro ao criar dashboard: {str(e)}", ephemeral=True)

    async def register_dashboard(self, interaction: discord.Interaction, project_id: int):
        guild = interaction.guild
        forum_channel = discord.utils.get(guild.forums, name=DASHBOARD_CHANNEL_NAME)

        try:
            await self.getProject(project_id)
        except Exception as e:
            await interaction.followup.send(
                f"❌ Projeto ID {project_id} não encontrado. Use o autocomplete para selecionar um projeto válido.",
                ephemeral=True)
            return

        project_name = self.project.name
        project_url = getattr(self.project, 'repository_url', '#')

        if not forum_channel:
            await interaction.followup.send(f"No '{DASHBOARD_CHANNEL_NAME}' forum channel found. Creating for u...")
            forum_channel = await guild.create_forum(
                name=DASHBOARD_CHANNEL_NAME,
                reason="Dashboard forum channel creation"
            )

        try:
            dashboard_image = await self.generate_dashboard_image()
        except FileNotFoundError:
            await interaction.followup.send("Error: Template files not found. Please check the file paths.")
            return
        except Exception as e:
            await interaction.followup.send(f"Error generating dashboard: {str(e)}")
            return

        view = DashboardView(project_name, project_url)

        discord_helper = await self.get_discord()
        self.category = await discord_helper.getCategory(int(self.project.group_id))

        # Check if a thread with the same name already exists
        existing_thread = discord.utils.get(forum_channel.threads, name=self.category.name.upper())

        if existing_thread:
            try:
                initial_message = await existing_thread.fetch_message(existing_thread.id)
                await initial_message.edit(content="", attachments=[dashboard_image], view=view)
                await interaction.followup.send(f"Dashboard for {self.category.name.upper()} updated.")
            except discord.NotFound:
                await self.create_new_post(interaction, forum_channel, self.category.name.upper(), dashboard_image,
                                           view)
        else:
            await self.create_new_post(interaction, forum_channel, self.category.name.upper(), dashboard_image, view)

        await interaction.followup.send(
            f"Dashboard for {project_name} created in the 'project-dashboards' forum channel.")

    async def generate_dashboard_image(self):
        project = self.project
        apm = AWSProject()

        with open(projectItemPath, 'r') as f:
            project_info_template = Template(f.read())

        project_info_html = ''
        project_last_run = None

        discord_helper = await self.get_discord()
        self.category = await discord_helper.getCategory(int(project.group_id))

        # Buscar todos os ambientes AWS configurados para este projeto
        aws_projects = await apm.get_aws_projects(project_id=project.id)

        if not aws_projects:
            # Se não tem ambientes AWS configurados, mostrar mensagem
            project_info_html = project_info_template.render(
                environment_name="Nenhum ambiente configurado",
                service_status="❌",
                last_update="N/A"
            )
        else:
            # Para cada ambiente AWS, buscar status do service ECS específico
            for aws_project in aws_projects:
                try:
                    # Verificar se tem cluster e service configurados
                    if not hasattr(aws_project, 'cluster_name') or not hasattr(aws_project, 'service_name'):
                        project_info_html += project_info_template.render(
                            environment_name=aws_project.environment.upper(),
                            service_status="⚠️",
                            last_update="Cluster/Service não configurado"
                        )
                        continue

                    if not aws_project.cluster_name or not aws_project.service_name:
                        project_info_html += project_info_template.render(
                            environment_name=aws_project.environment.upper(),
                            service_status="⚠️",
                            last_update="Cluster/Service não configurado"
                        )
                        continue

                    aws_manager = AWSResourceManager(
                        aws_project.aws_access_key,
                        aws_project.aws_secret_key,
                        aws_project.aws_region
                    )

                    # Buscar informações do service específico
                    service_info = aws_manager.get_specific_service_info(
                        aws_project.cluster_name,
                        aws_project.service_name
                    )

                    if service_info:
                        status_emoji_value = self.get_ecs_status_emoji(service_info['status'])
                        last_update = service_info['last_update']

                        # Formatar data de última atualização com timezone da região AWS
                        if last_update:
                            local_timezone = self.get_timezone_from_aws_region([aws_project])
                            last_update_local = last_update.astimezone(local_timezone)
                            formatted_date = format_date(last_update_local.strftime("%Y-%m-%d %H:%M:%SZ"))
                            if project_last_run is None or last_update > project_last_run:
                                project_last_run = last_update
                        else:
                            formatted_date = "Nunca executado"

                        project_info_html += project_info_template.render(
                            environment_name=aws_project.environment.upper(),
                            service_status=f"{status_emoji_value}",
                            last_update=formatted_date
                        )
                    else:
                        # Service não encontrado
                        project_info_html += project_info_template.render(
                            environment_name=aws_project.environment.upper(),
                            service_status="❌",
                            last_update="Service não encontrado"
                        )

                except Exception as e:
                    # Em caso de erro, mostrar ambiente com erro
                    project_info_html += project_info_template.render(
                        environment_name=aws_project.environment.upper(),
                        service_status="❌",
                        last_update=f"Erro: {str(e)[:30]}..."
                    )

        # Para o updated_at da dashboard, sempre usar o momento atual UTC
        dashboard_generated_at = datetime.now(timezone.utc)

        # Load and render the HTML templates
        with open(overviewPath, 'r') as f:
            overview_template = Template(f.read())

        overview_html = overview_template.render(
            project_icon="🚀",
            project_name=self.category.name,
            updated_at=format_date(dashboard_generated_at.strftime("%Y-%m-%d %H:%M:%SZ")),
            repositories_box_content=project_info_html,
            progress_bar_value=0,  # Removido barra de progresso
            resource_use="N/A",  # Removido uso de recursos
            instances_count=0  # Removido contagem de instâncias
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

    async def create_new_post(self, interaction, forum_channel, project_name, dashboard_image, view):
        thread, message = await forum_channel.create_thread(
            name=project_name,
            content="",
            file=dashboard_image,
            view=view
        )
        self.dashboard_posts[project_name] = thread.id

    async def update_dashboards_periodically(self):
        print("Update Dashboard Task Started")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            print("Update Dashboard Task: Updating dashboards...")

            try:
                discord_helper = await self.get_discord()
                guild = self.bot.guilds[0]

                for category in guild.categories:
                    projects = await Project().get_projects_by_group_id(category.id)
                    for project in projects:
                        forum_channel = discord.utils.get(guild.forums, name=DASHBOARD_CHANNEL_NAME)
                        if forum_channel:
                            try:
                                await self.getProject(project.id)
                                project_name = self.project.name

                                view = DashboardView(project_name, getattr(self.project, 'repository_url', '#'))
                                dashboard_image = await self.generate_dashboard_image()

                                # Check if a thread with the same name already exists
                                existing_thread = discord.utils.get(forum_channel.threads,
                                                                    name=self.category.name.upper())

                                if existing_thread:
                                    try:
                                        initial_message = await existing_thread.fetch_message(existing_thread.id)
                                        await initial_message.edit(content="", attachments=[dashboard_image], view=view)
                                    except discord.NotFound:
                                        thread, message = await forum_channel.create_thread(
                                            name=self.category.name.upper(),
                                            content="",
                                            file=dashboard_image,
                                            view=view
                                        )
                                        self.dashboard_posts[project_name] = thread.id

                            except discord.NotFound:
                                print(f"Dashboard thread for {project_name} not found. Removing from tracking.")
                                if project_name in self.dashboard_posts:
                                    del self.dashboard_posts[project_name]
                            except Exception as e:
                                print(f"Error updating dashboard for {project_name}: {str(e)}")

                print("Update Dashboard Task: Dashboards updated.")

            except Exception as e:
                print(f"Error in update_dashboards_periodically: {str(e)}")

            await asyncio.sleep(60 * 5)  # Update every 5 minutes


async def setup(bot):
    print("DashboardCog setup() sendo executado")
    await DashboardCog.register(bot)


print("DashboardCog terminou de ser importado")