import asyncio
import discord
from discord import app_commands, AllowedMentions
from typing import Optional

from actions.project import ProjectActions
from core.cogs.commands_cog import CommandsCog
from core.db.gitlab import Gitlab
from core.db.project import Project
from helpers.chunk import markdown_aware_chunk
from helpers.cog import need_admin_permissions
from helpers.messages import HELP_MESSAGE_CONTENT
from helpers.utils import response_list

class AdminCommands(CommandsCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.project = Project()
        self.gitlab = Gitlab()

    @app_commands.command(name='limpar', description="Limpa mensagens do canal")
    @need_admin_permissions()
    async def clear(self, interaction: discord.Interaction, amount: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        if amount is None:
            await interaction.followup.send('Por favor, especifique o número de mensagens a serem apagadas.')
            return

        if amount.lower() in ("all", "tudo"):
            await interaction.followup.send("Iniciando a limpeza de todas as mensagens. Isso pode levar algum tempo...")

            try:
                while True:
                    deleted = await channel.purge(limit=100)
                    if len(deleted) < 100:
                        break
                    await asyncio.sleep(1)
            except discord.errors.Forbidden:
                await interaction.followup.send("Não tenho permissão para apagar mensagens neste canal.")
            except Exception as e:
                await interaction.followup.send(f"Ocorreu um erro: {str(e)}")
            else:
                await interaction.followup.send("Limpeza concluída. Todas as mensagens recentes foram apagadas.")
            return

        try:
            num = int(amount)
            if num <= 0 or num > 100:
                raise ValueError()
        except ValueError:
            await interaction.followup.send('Por favor, forneça um número válido de 1 a 100.')
            return

        await channel.purge(limit=num + 1)
        await interaction.followup.send(f'{num} mensagens foram apagadas.')

    @app_commands.command(name='ajuda', description="Exibe as mensagens de ajuda")
    async def help_command(self, interaction: discord.Interaction):
        await response_list(
            interaction,
            HELP_MESSAGE_CONTENT,
            cap=2000,
            is_markdown=True,
            error_message="❌ Erro: Conteúdo de ajuda não disponível."
        )

    @app_commands.command(name='config_gitlab', description="Configura a URL e o token do GitLab")
    @need_admin_permissions()
    async def config_gitlab(self, interaction: discord.Interaction, url: str, token: str):
        self.logger.info('Config GitLab command triggered')
        await self.gitlab.set_gitlab_config('url', url)
        await self.gitlab.set_gitlab_config('token', token)
        await interaction.response.send_message("Configuração do GitLab atualizada com sucesso!")

    @app_commands.command(name='add_project', description="Adiciona um novo projeto")
    @need_admin_permissions()
    async def add_project(self, interaction: discord.Interaction, project_id: int):
        if not interaction.guild:
            await interaction.response.send_message("Este comando só pode ser usado em servidores.")
            return

        project = ProjectActions(interaction.guild)
        await project.add(project_id)

        await interaction.response.send_message(f"Projeto {project_id} adicionado com sucesso!")
        self.logger.info(f'Projeto {project_id} adicionado com sucesso')

    @app_commands.command(name='remove_project', description="Remove um projeto existente")
    @need_admin_permissions()
    async def remove_project(self, interaction: discord.Interaction, project_id: int):
        if not interaction.guild:
            await interaction.response.send_message("Este comando só pode ser usado em servidores.")
            return

        project = ProjectActions(interaction.guild)
        await project.load(project_id)
        await project.remove()

        await interaction.response.send_message(f"Projeto {project_id} removido com sucesso!")
        self.logger.info(f'Projeto {project_id} removido com sucesso')

    @app_commands.command(name='show_config', description="Mostra a configuração atual do GitLab e projetos")
    @need_admin_permissions()
    async def show_config(self, interaction: discord.Interaction):
        self.logger.info('Show config command triggered')
        gitlab_url = await self.gitlab.get_gitlab_config('url')

        print(f"gitlab_url: {gitlab_url}")

        projects = await self.project.get_projects()

        print(f"projects: {projects}")

        config_message = "Configuração atual do bot:\n\n"
        config_message += f"GitLab URL: {gitlab_url}\n\n"

        config_message += "Projetos:\n"
        for project in projects:
            project_id, project_name, project_group, *other_values = project
            config_message += f"- {project_group.upper()} > {project_name}\n"

        await interaction.response.send_message(config_message)


# Setup da cog
async def setup(bot):
    print("AdminCommands setup() sendo executado")
    await AdminCommands.register(bot)

print("admin_commands.py terminou de ser importado")
