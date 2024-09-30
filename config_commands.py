# !config_gitlab <url> <token>: Set the GitLab URL and access token.
# !add_project <project_id> <project_name>: Add a GitLab project to monitor.
# !add_role <role> <email>: Associate a role with a GitLab user's email.
# !add_notification <event_type> <role>: Configure which roles should be notified for specific event types.
# !show_config: Display the current bot configuration.

from discord.ext import commands
from config import Config
from notification_templates import get_help_message, get_success_message, get_config_message

class ConfigCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config()
        print("ConfigCommands cog iniciado.")

    @commands.command(name='ajuda')
    async def help_command(self, ctx):
        """Mostra a mensagem de ajuda com todos os comandos disponíveis."""
        print("Comando de ajuda acionado.")
        await ctx.send(get_help_message())

    @commands.command(name='config_gitlab')
    @commands.has_permissions(administrator=True)
    async def config_gitlab(self, ctx, url: str, token: str):
        """Configura a URL e o token de acesso do GitLab."""
        await self.config.set_gitlab_config('url', url)
        await self.config.set_gitlab_config('token', token)
        await ctx.send(get_success_message('gitlab_config'))

    @commands.command(name='add_project')
    @commands.has_permissions(administrator=True)
    async def add_project(self, ctx, project_id: int, *, project_name: str):
        """Adiciona um projeto do GitLab para monitoramento."""
        await self.config.add_project(project_id, project_name)
        await ctx.send(get_success_message('project_added', project_name=project_name, project_id=project_id))

    @commands.command(name='add_role')
    @commands.has_permissions(administrator=True)
    async def add_role(self, ctx, role: str, email: str):
        """Associa uma função a um email do GitLab."""
        await self.config.add_role(role, email)
        await ctx.send(get_success_message('role_added', role=role, email=email))

    @commands.command(name='add_notification')
    @commands.has_permissions(administrator=True)
    async def add_notification(self, ctx, event_type: str, role: str):
        """Configura notificações para uma função."""
        await self.config.add_notification(event_type, role)
        await ctx.send(get_success_message('notification_added', event_type=event_type, role=role))

    @commands.command(name='show_config')
    @commands.has_permissions(administrator=True)
    async def show_config(self, ctx):
        """Mostra a configuração atual do bot."""
        gitlab_url = await self.config.get_gitlab_config('url')
        projects = await self.config.get_projects()
        roles = await self.config.get_roles()
        notifications = await self.config.get_notifications()

        config_message = get_config_message(gitlab_url, projects, roles, notifications)
        await ctx.send(config_message)

def setup(bot):
    bot.add_cog(ConfigCommands(bot))
    print("ConfigCommands cog configurado.")