import asyncio
import discord
from discord.ext import commands
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

    @commands.command(name='limpar')
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount = None):
        if amount is None:
            await ctx.send('Por favor, especifique o número de mensagens a serem apagadas.')
            return
        
        if amount == "all" or amount == "tudo":
            await ctx.send("Iniciando a limpeza de todas as mensagens. Isso pode levar algum tempo...")
            
            try:
                while True:
                    deleted = await ctx.channel.purge(limit=100)
                    if len(deleted) < 100:
                        break
                    await asyncio.sleep(1)  # Pausa breve para evitar atingir limites de taxa
            except discord.errors.Forbidden:
                await ctx.send("Não tenho permissão para apagar mensagens neste canal.")
            except Exception as e:
                await ctx.send(f"Ocorreu um erro: {str(e)}")
            else:
                await ctx.send("Limpeza concluída. Todas as mensagens recentes foram apagadas.", delete_after=15)
            return

        try:
            amount = int(amount)
        except ValueError:
            await ctx.send('Por favor, forneça um número válido de mensagens para apagar.')
            return

        if amount <= 0:
            await ctx.send('O número de mensagens deve ser maior que zero.')
            return

        if amount > 100:
            await ctx.send('Você só pode apagar até 100 mensagens de uma vez.')
            return

        await ctx.channel.purge(limit=amount + 1)  # +1 para incluir o comando
        await ctx.send(f'{amount} mensagens foram apagadas.', delete_after=5)

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Você não tem permissão para usar este comando.")
            
    @commands.command(name='ajuda')
    async def help_command(self, ctx):
        self.logger.info('Comando de ajuda acionado')
        help_messages = HELP_MESSAGE_CONTENT
        
        for message in help_messages:
            await ctx.send(message)

    @commands.command(name='config_gitlab')
    @commands.has_permissions(administrator=True)
    async def config_gitlab(self, ctx, url: str, token: str):
        self.logger.info('Config GitLab command triggered')
        await self.gitlab.set_gitlab_config('url', url)
        await self.gitlab.set_gitlab_config('token', token)
        await ctx.send("Configuração do GitLab atualizada com sucesso!")

    @commands.command(name='add_project')
    @commands.has_permissions(administrator=True)
    async def add_project(self, ctx, project_id: int):
        project = ProjectActions(ctx.guild)
        await project.add(project_id)

        await ctx.send(f"Projeto {project_id} adicionado com sucesso!")
        self.logger.info(f'Projeto {project_id} adicionado com sucesso')

    @commands.command(name='remove_project')
    @commands.has_permissions(administrator=True)
    async def remove_project(self, ctx, project_id: int):
        project = ProjectActions(ctx.guild)
        await project.load(project_id)
        await project.remove()
        
        await ctx.send(f"Projeto {project_id} removido com sucesso!")
        self.logger.info(f'Projeto {project_id} removido com sucesso')

    @commands.command(name='show_config')
    @commands.has_permissions(administrator=True)
    async def show_config(self, ctx):
        self.logger.info('Show config command triggered')
        gitlab_url = await self.gitlab.get_gitlab_config('url')
        projects = await self.project.get_projects()

        config_message = "Configuração atual do bot:\n\n"
        config_message += f"GitLab URL: {gitlab_url}\n\n"
        
        self.logger.info(f'projects: {projects}')

        config_message += "Projetos:\n"
        for project in projects:
            project_id, project_name, project_group, *other_values = project
            config_message += f"- {project_group.upper()} > {project_name}\n"

        await ctx.send(config_message)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))