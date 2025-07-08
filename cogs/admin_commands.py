import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Optional
import asyncio
import datetime

# Imports ajustados para a estrutura do projeto
try:
    from actions.project import ProjectActions
except ImportError:
    print("Warning: ProjectActions not found, some commands may not work")
    ProjectActions = None

try:
    from core.cogs.commands_cog import CommandsCog
except ImportError:
    print("Warning: CommandsCog not found, using commands.Cog")
    CommandsCog = commands.Cog

try:
    from core.db.gitlab import Gitlab
    from core.db.project import Project
except ImportError:
    print("Warning: Database classes not found")
    Gitlab = None
    Project = None

try:
    from helpers.messages import HELP_MESSAGE_CONTENT
except ImportError:
    HELP_MESSAGE_CONTENT = ["📚 **Bot Help**\n\nComandos disponíveis:"]


class AdminCommands(CommandsCog if CommandsCog != commands.Cog else commands.Cog):
    """Comandos administrativos do bot"""

    def __init__(self, bot):
        if CommandsCog != commands.Cog:
            super().__init__(bot, loggerTag='admin')
        else:
            super().__init__()

        self.bot = bot

        # Inicializar classes apenas se estiverem disponíveis
        self.project = Project() if Project else None
        self.gitlab = Gitlab() if Gitlab else None

    @app_commands.command(name="clear", description="Clear messages from the channel")
    @app_commands.describe(
        amount="Number of messages to delete or 'all' for all messages"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: str):
        """Limpa mensagens do canal"""
        if amount.lower() == "all" or amount.lower() == "tudo":
            await interaction.response.defer()

            try:
                deleted = 0
                while True:
                    deleted_msgs = await interaction.channel.purge(limit=100)
                    if len(deleted_msgs) < 100:
                        deleted += len(deleted_msgs)
                        break
                    deleted += 100
                    await asyncio.sleep(1)

                await interaction.followup.send(f"🧹 Limpei {deleted} mensagens.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("❌ Não tenho permissão para deletar mensagens.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            return

        try:
            amt = int(amount)
            if amt <= 0:
                await interaction.response.send_message("❌ Quantidade deve ser maior que 0.", ephemeral=True)
                return

            if amt > 100:
                await interaction.response.send_message("❌ Máximo de 100 mensagens por vez.", ephemeral=True)
                return

            await interaction.response.defer()
            deleted = await interaction.channel.purge(limit=amt)
            await interaction.followup.send(f"🧹 Deletei {len(deleted)} mensagens.", ephemeral=True)

        except ValueError:
            await interaction.response.send_message("❌ Forneça um número válido.", ephemeral=True)

    @app_commands.command(name="ajuda", description="Mostra informações de ajuda detalhadas do bot")
    async def help_command(self, interaction: discord.Interaction):
        """Comando de help com debug completo"""
        try:
            print(f"🔍 Debug: Comando /ajuda executado por {interaction.user}")

            # Verificar se interaction está válido
            if not interaction:
                print("❌ Debug: Interaction é None")
                return

            print("✅ Debug: Interaction válido")

            # Criar embed com tratamento de erro
            try:
                embed = discord.Embed(
                    title="🤖 Gino - Bot de Integração GitLab",
                    description="**Comandos Administrativos Disponíveis:**",
                    color=discord.Color.blue()
                )
                print("✅ Debug: Embed criado")
            except Exception as e:
                print(f"❌ Debug: Erro ao criar embed: {e}")
                # Fallback sem embed
                await interaction.response.send_message(
                    "**🤖 Gino - Comandos Disponíveis:**\n\n"
                    "• `/clear` - Limpar mensagens\n"
                    "• `/show_config` - Ver configuração\n"
                    "• `/show_projects` - Listar projetos\n"
                    "• `/config_gitlab` - Configurar GitLab",
                    ephemeral=True
                )
                return

            # Adicionar campos ao embed
            try:
                admin_commands = [
                    "`/clear <quantidade>` - Limpa mensagens do canal",
                    "`/config_gitlab <url> <token>` - Configura integração GitLab",
                    "`/add_project <id>` - Adiciona novo projeto",
                    "`/remove_project <id>` - Remove projeto",
                    "`/show_config` - Mostra configuração atual",
                    "`/show_projects` - Lista todos os projetos",
                    "`/migrate_data` - Migra dados para servidor atual",
                    "`/recreate_webhooks` - Recria webhooks do GitLab"
                ]

                embed.add_field(
                    name="🔧 Comandos Disponíveis",
                    value="\n".join(admin_commands),
                    inline=False
                )

                embed.add_field(
                    name="⚠️ Importante",
                    value="• Comandos requerem permissões de administrador\n• Todos os comandos estão funcionando!",
                    inline=False
                )

                embed.set_footer(text="🦖 Gino - O Bot Supremo")
                print("✅ Debug: Campos adicionados ao embed")

            except Exception as e:
                print(f"❌ Debug: Erro ao adicionar campos: {e}")

            # Enviar resposta
            try:
                print("🔍 Debug: Tentando enviar resposta...")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                print("✅ Debug: Resposta enviada com sucesso!")

            except discord.InteractionResponded:
                print("⚠️ Debug: Interaction já foi respondido, usando followup")
                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                print(f"❌ Debug: Erro ao enviar resposta: {e}")
                # Ultimo fallback - resposta simples
                try:
                    await interaction.response.send_message(
                        "🤖 **Gino Bot** - Comandos: /clear, /show_config, /show_projects",
                        ephemeral=True
                    )
                except:
                    print("❌ Debug: Falha total ao responder")

        except Exception as e:
            print(f"💥 Debug: Erro geral no comando ajuda: {e}")
            print(f"💥 Debug: Tipo do erro: {type(e)}")
            import traceback
            traceback.print_exc()

            # Tentar resposta de emergência
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ Erro interno no comando. Tente `/show_config`",
                        ephemeral=True
                    )
            except:
                pass


    async def help_command_old(self, interaction: discord.Interaction):
        """Mostra informações de ajuda do bot"""
        embed = discord.Embed(
            title="🤖 Gino - Bot de Integração GitLab",
            description="Comandos disponíveis:",
            color=discord.Color.blue()
        )

        # Comandos administrativos
        admin_commands = [
            "`/clear` - Limpa mensagens do canal",
            "`/config_gitlab` - Configura integração GitLab",
            "`/add_project` - Adiciona novo projeto",
            "`/remove_project` - Remove projeto",
            "`/show_config` - Mostra configuração atual",
            "`/show_projects` - Lista todos os projetos",
            "`/migrate_data` - Migra dados para servidor atual",
            "`/recreate_webhooks` - Recria webhooks do GitLab"
        ]

        embed.add_field(
            name="🔧 Comandos Administrativos",
            value="\n".join(admin_commands),
            inline=False
        )

        embed.set_footer(text="Use os comandos com cuidado! Alguns requerem permissões de administrador.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="config_gitlab", description="Configure GitLab integration")
    @app_commands.describe(
        url="GitLab instance URL",
        token="GitLab access token"
    )
    # @app_commands.checks.has_permissions(administrator=True)
    async def config_gitlab(self, interaction: discord.Interaction, url: str, token: str):
        """Configura integração com GitLab"""
        if not self.gitlab:
            await interaction.response.send_message("❌ Sistema GitLab não disponível.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            await self.gitlab.set_gitlab_config('url', url)
            await self.gitlab.set_gitlab_config('token', token)
            await interaction.followup.send("✅ Configuração GitLab atualizada!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao configurar: {str(e)}", ephemeral=True)

    async def get_project_suggestions(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[int]]:
        """Autocomplete para projetos"""
        if not self.project:
            return []

        try:
            projects = await self.project.get_projects()
            return [
                       app_commands.Choice(name=f"{name} ({id})", value=id)
                       for id, name, _, _ in projects
                       if current.lower() in name.lower() or str(id).startswith(current)
                   ][:25]
        except:
            return []

    @app_commands.command(name="add_project", description="Add a new project")
    @app_commands.describe(project_id="Project ID to add")
    @app_commands.autocomplete(project_id=get_project_suggestions)
    # @app_commands.checks.has_permissions(administrator=True)
    async def add_project(self, interaction: discord.Interaction, project_id: int):
        """Adiciona um novo projeto"""
        if not ProjectActions:
            await interaction.response.send_message("❌ Sistema de projetos não disponível.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            project = ProjectActions(interaction.guild)
            await project.add(project_id)
            await interaction.followup.send(f"✅ Projeto {project_id} adicionado!")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao adicionar projeto: {str(e)}")

    # @app_commands.command(name="remove_project", description="Remove a project")
    # @app_commands.describe(project_id="Project ID to remove")
    # @app_commands.autocomplete(project_id=get_project_suggestions)
    # # @app_commands.checks.has_permissions(administrator=True)
    # async def remove_project(self, interaction: discord.Interaction, project_id: int):
    #     """Remove um projeto"""
    #     if not ProjectActions:
    #         await interaction.response.send_message("❌ Sistema de projetos não disponível.", ephemeral=True)
    #         return
    #
    #     await interaction.response.defer()
    #
    #     try:
    #         project = ProjectActions(interaction.guild)
    #         await project.load(project_id)
    #         await project.remove()
    #         await interaction.followup.send(f"✅ Projeto {project_id} removido!")
    #     except Exception as e:
    #         await interaction.followup.send(f"❌ Erro ao remover projeto: {str(e)}")

    @app_commands.command(name="show_config", description="Show current bot configuration")
    # @app_commands.checks.has_permissions(administrator=True)
    async def show_config(self, interaction: discord.Interaction):
        """Mostra configuração atual do bot"""
        await interaction.response.defer()

        embed = discord.Embed(
            title="⚙️ Configuração do Bot",
            color=discord.Color.blue()
        )

        try:
            if self.gitlab:
                gitlab_url = await self.gitlab.get_gitlab_config('url')
                embed.add_field(
                    name="🔗 GitLab URL",
                    value=gitlab_url or "Não configurado",
                    inline=False
                )

            if self.project:
                projects = await self.project.get_projects()
                projects_text = ""
                for project in projects:
                    project_id, project_name, project_group, *_ = project
                    projects_text += f"• {project_group.upper()} > {project_name} (ID: {project_id})\n"

                embed.add_field(
                    name="📊 Projetos",
                    value=projects_text if projects_text else "Nenhum projeto configurado",
                    inline=False
                )
        except Exception as e:
            embed.add_field(
                name="❌ Erro",
                value=f"Erro ao carregar configurações: {str(e)}",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="show_projects", description="Mostra todos os projetos no banco de dados")
    # @app_commands.checks.has_permissions(administrator=True)
    async def show_projects(self, interaction: discord.Interaction):
        """Mostra todos os projetos salvos no banco"""
        await interaction.response.defer(ephemeral=True)

        if not self.project:
            await interaction.followup.send("❌ Sistema de projetos não disponível.", ephemeral=True)
            return

        try:
            projects = await self.project.get_projects()

            if not projects:
                await interaction.followup.send("📭 Nenhum projeto encontrado.", ephemeral=True)
                return

            embed = discord.Embed(
                title="📊 Projetos no Banco de Dados",
                color=discord.Color.blue()
            )

            for project_data in projects:
                project_id, project_name, group_name, repository_url, channel_id, group_id, thread_id = project_data

                embed.add_field(
                    name=f"{group_name.upper()} > {project_name}",
                    value=f"**ID:** {project_id}\n**Canal:** <#{channel_id}>\n**Categoria:** <#{group_id}>",
                    inline=False
                )

            embed.set_footer(text=f"Total: {len(projects)} projetos")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)

    @app_commands.command(name="migrate_data", description="Migra dados do banco para o servidor atual")
    @app_commands.describe(backup_projects="Fazer backup dos projetos atuais antes da migração")
    # @app_commands.checks.has_permissions(administrator=True)
    async def migrate_data(self, interaction: discord.Interaction, backup_projects: bool = True):
        """Migra dados para o servidor atual"""
        await interaction.response.defer(ephemeral=True)

        if not self.project:
            await interaction.followup.send("❌ Sistema de projetos não disponível.", ephemeral=True)
            return

        try:
            projects = await self.project.get_projects()

            if not projects:
                await interaction.followup.send("❌ Nenhum projeto encontrado.", ephemeral=True)
                return

            guild = interaction.guild
            migration_report = []

            await interaction.followup.send("🔄 Iniciando migração...", ephemeral=True)

            for project_data in projects:
                project_id, project_name, group_name, repository_url, channel_id, group_id, thread_id = project_data

                try:
                    # Criar categoria se não existir
                    category = discord.utils.get(guild.categories, name=group_name.upper())
                    if not category:
                        category = await guild.create_category(group_name.upper())
                        migration_report.append(f"✅ Categoria criada: {group_name.upper()}")

                    # Criar canal se não existir
                    channel = discord.utils.get(category.channels, name=project_name.lower())
                    if not channel:
                        channel = await category.create_text_channel(
                            project_name.lower(),
                            topic=f"Projeto GitLab: {project_name} (ID: {project_id})"
                        )
                        migration_report.append(f"✅ Canal criado: #{project_name.lower()}")

                    # Atualizar banco
                    await self.project.set_project(
                        project_id, project_name, group_name,
                        channel.id, category.id, repository_url, thread_id
                    )

                    migration_report.append(f"📊 {project_name} migrado!")

                except Exception as e:
                    migration_report.append(f"❌ Erro em {project_name}: {str(e)}")

            report = f"# 🚀 Migração Concluída\n\n" + "\n".join(migration_report)

            if len(report) > 2000:
                with open("migration_report.txt", "w", encoding="utf-8") as f:
                    f.write(report)
                await interaction.followup.send(
                    "📄 Relatório completo:",
                    file=discord.File("migration_report.txt"),
                    ephemeral=True
                )
            else:
                await interaction.followup.send(f"```\n{report}\n```", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro na migração: {str(e)}", ephemeral=True)

    @app_commands.command(name="recreate_webhooks", description="Recria todos os webhooks do GitLab")
    # @app_commands.checks.has_permissions(administrator=True)
    async def recreate_webhooks(self, interaction: discord.Interaction):
        """Recria webhooks para todos os projetos"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Aqui você implementaria a lógica de recriar webhooks
            # Por enquanto, apenas uma mensagem de placeholder
            await interaction.followup.send("🔄 Funcionalidade em desenvolvimento...", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Tratamento de erros dos comandos"""
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "❌ Você não tem permissão para este comando.",
                ephemeral=True
            )
        else:
            error_msg = f"❌ Erro no comando: {str(error)}"

            if interaction.response.is_done():
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await interaction.response.send_message(error_msg, ephemeral=True)


# Função setup SIMPLIFICADA - SEM sync automático
async def setup(bot):
    cog = AdminCommands(bot)
    await bot.add_cog(cog)