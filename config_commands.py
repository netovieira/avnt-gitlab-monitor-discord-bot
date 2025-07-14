# !config_gitlab <url> <token>: Set the GitLab URL and access token.
# !set_project <project_id> <project_name>: Add a GitLab project to monitor.
# !add_role <role> <email>: Associate a role with a GitLab user's email.
# !add_notification <event_type> <role>: Configure which roles should be notified for specific event types.
# !show_config: Display the current bot configuration.

from discord.ext import commands
from Config import Config
from core.db.gitlab import Gitlab
from core.db.project import Project
from notification_templates import get_help_message, get_success_message, get_config_message

class ConfigCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.project = Project()
        self.gitlab = Gitlab()
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
        await self.gitlab.set_gitlab_config('url', url)
        await self.gitlab.set_gitlab_config('token', token)
        await ctx.send(get_success_message('gitlab_config'))

    @commands.command(name='show_config')
    @commands.has_permissions(administrator=True)
    async def show_config(self, ctx):
        """Mostra a configuração atual do bot."""
        gitlab_url = await self.gitlab.get_gitlab_config('url')
        projects = await self.project.get_projects()

        config_message = get_config_message(gitlab_url, projects)
        await ctx.send(config_message)

def setup(bot):
    bot.add_cog(ConfigCommands(bot))
    print("ConfigCommands cog configurado.")