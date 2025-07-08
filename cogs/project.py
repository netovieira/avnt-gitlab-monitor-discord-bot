import discord
from discord import app_commands
from typing import Dict, Optional, List
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
        self.project_manager = ProjectActions(bot.guilds[0] if bot.guilds else None)
        self.aws_credentials_manager = AWSCredentialsManager()

    async def environment_autocomplete(self,
                                       interaction: discord.Interaction,
                                       current: str,
                                       ) -> List[app_commands.Choice[str]]:
        environments = ['dev', 'qa', 'staging', 'prod']
        return [
            app_commands.Choice(name=env, value=env)
            for env in environments
            if current.lower() in env.lower()
        ]

    async def aws_profile_autocomplete(self,
                                       interaction: discord.Interaction,
                                       current: str,
                                       ) -> List[app_commands.Choice[str]]:
        try:
            profiles = self.aws_credentials_manager.list_profiles()
            return [
                       app_commands.Choice(name=profile, value=profile)
                       for profile in profiles
                       if current.lower() in profile.lower()
                   ][:25]  # Discord limit
        except Exception:
            return []

    async def process_aws_credentials(self,
                                      interaction: discord.Interaction,
                                      aws_profile: Optional[str] = None,
                                      aws_access_key: Optional[str] = None,
                                      aws_secret_key: Optional[str] = None,
                                      aws_region: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Process and validate AWS credentials from either profile or custom credentials"""
        try:
            if aws_profile:
                credentials = self.aws_credentials_manager.get_profile_credentials(aws_profile)
                source = f"profile '{aws_profile}'"
            else:
                if not all([aws_access_key, aws_secret_key, aws_region]):
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "❌ Quando não usar um perfil, você deve fornecer access key, secret key e region.",
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            "❌ Quando não usar um perfil, você deve fornecer access key, secret key e region.",
                            ephemeral=True
                        )
                    return None

                credentials = {
                    'aws_access_key': aws_access_key,
                    'aws_secret_key': aws_secret_key,
                    'aws_region': aws_region
                }
                source = "credenciais customizadas"

            is_valid, message = self.aws_credentials_manager.validate_credentials(credentials)
            if not is_valid:
                error_msg = f"❌ Credenciais AWS inválidas de {source}: {message}"
                if not interaction.response.is_done():
                    await interaction.response.send_message(error_msg, ephemeral=True)
                else:
                    await interaction.followup.send(error_msg, ephemeral=True)
                return None

            return credentials

        except ValueError as e:
            error_msg = f"❌ {str(e)}"
            if not interaction.response.is_done():
                await interaction.response.send_message(error_msg, ephemeral=True)
            else:
                await interaction.followup.send(error_msg, ephemeral=True)
            return None
        except Exception as e:
            error_msg = f"❌ Erro ao processar credenciais AWS: {str(e)}"
            if not interaction.response.is_done():
                await interaction.response.send_message(error_msg, ephemeral=True)
            else:
                await interaction.followup.send(error_msg, ephemeral=True)
            return None

    async def set_project(self, id: int, project_name: str = None, project_group: str = None):
        self.project_id = id
        self.project = await self.project_manager.load(id)

        if not self.project:
            raise ValueError(f"Projeto com ID {id} não existe. Configure o projeto primeiro.")
        return self.project

    @app_commands.command(name="register_project", description="Registrar um novo projeto com configuração AWS")
    @app_commands.describe(
        project_id="ID do Projeto",
        environment="Ambiente (dev/qa/staging/prod)",
        name="Nome customizado do projeto",
        group="Nome customizado do grupo do projeto",
        profile="Nome do perfil AWS",
        key="Chave de acesso AWS",
        secret="Chave secreta AWS",
        region="Região AWS"
    )
    @app_commands.autocomplete(
        environment=environment_autocomplete,
        profile=aws_profile_autocomplete
    )
    @app_commands.default_permissions(administrator=True)
    async def register_project(
            self,
            interaction: discord.Interaction,
            project_id: int,
            environment: str,
            name: Optional[str] = None,
            group: Optional[str] = None,
            profile: Optional[str] = None,
            key: Optional[str] = None,
            secret: Optional[str] = None,
            region: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            # Primeiro tenta carregar o projeto
            await self.set_project(project_id)
            await self._configure_project(interaction, name or self.project["name"],
                                          group or self.project["group_name"])

            # Processa credenciais AWS
            credentials = await self.process_aws_credentials(
                interaction,
                aws_profile=profile,
                aws_access_key=key,
                aws_secret_key=secret,
                aws_region=region
            )

            if credentials:
                await self.project_manager.add_aws_environment(
                    project_id=project_id,
                    environment=environment,
                    **credentials
                )

                # Tenta criar dashboard se disponível
                try:
                    from cogs.dashboard import DashboardCog
                    dashboard_cog = self.bot.get_cog('DashboardCog')
                    if dashboard_cog:
                        await dashboard_cog.register_dashboard(interaction, project_id)
                except Exception as e:
                    self.logger.warning(f"Could not create dashboard: {e}")

                await interaction.followup.send(
                    f"✅ Projeto {project_id} registrado com sucesso com configuração AWS!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Falha ao processar credenciais AWS.",
                    ephemeral=True
                )

        except Exception as e:
            self.logger.error(f"Error in register_project: {e}")
            await interaction.followup.send(
                f"❌ Ocorreu um erro: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="configure_project", description="Configurar um novo projeto ou atualizar existente")
    @app_commands.describe(
        project_id="ID do Projeto",
        name="Nome customizado do projeto",
        group="Nome customizado do grupo do projeto"
    )
    @app_commands.default_permissions(administrator=True)
    async def configure_project(
            self,
            interaction: discord.Interaction,
            project_id: int,
            name: Optional[str] = None,
            group: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            await self.set_project(project_id)
            await self._configure_project(
                interaction,
                name or self.project["name"],
                group or self.project["group_name"].upper()
            )
        except Exception as e:
            self.logger.error(f"Error in configure_project: {e}")
            await interaction.followup.send(
                f"❌ Ocorreu um erro: {str(e)}",
                ephemeral=True
            )

    async def _configure_project(self, interaction: discord.Interaction, project_name: str, project_group: str):
        try:
            await self.project_manager.add(self.project_id, project_name, project_group)
            await interaction.followup.send(
                f"✅ Projeto {project_name} (ID: {self.project_id}) foi configurado com sucesso no grupo {project_group}.",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Error configuring project: {str(e)}")
            raise

    @app_commands.command(name="list_projects", description="Listar todos os projetos configurados")
    @app_commands.default_permissions(administrator=True)
    async def list_projects(self, interaction: discord.Interaction):
        try:
            projects = await self.project_manager.get_projects()
            if not projects:
                await interaction.response.send_message(
                    "📋 Nenhum projeto foi configurado ainda.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="📋 Projetos Configurados",
                color=discord.Color.blue()
            )

            for project in projects:
                project_id, name, group, *_ = project
                embed.add_field(
                    name=f"{name} (ID: {project_id})",
                    value=f"Grupo: {group}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error listing projects: {str(e)}")
            await interaction.response.send_message(
                f"❌ Erro ao listar projetos: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="remove_project", description="Remover um projeto configurado")
    @app_commands.describe(project_id="ID do projeto para remover")
    @app_commands.default_permissions(administrator=True)
    async def remove_project(self, interaction: discord.Interaction, project_id: int):
        await interaction.response.defer(ephemeral=True)

        try:
            await self.project_manager.remove_project(project_id)
            await interaction.followup.send(
                f"✅ Projeto com ID {project_id} foi removido com sucesso.",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Error removing project: {str(e)}")
            await interaction.followup.send(
                f"❌ Erro ao remover projeto: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="configure_aws", description="Configurar credenciais AWS para um projeto")
    @app_commands.describe(
        project_id="ID do Projeto",
        environment="Ambiente (dev/qa/staging/prod)",
        profile="Nome do perfil AWS (opcional)",
        key="Chave de acesso AWS (se não usar perfil)",
        secret="Chave secreta AWS (se não usar perfil)",
        region="Região AWS (se não usar perfil)"
    )
    @app_commands.autocomplete(
        environment=environment_autocomplete,
        profile=aws_profile_autocomplete
    )
    @app_commands.default_permissions(administrator=True)
    async def configure_aws_project(
            self,
            interaction: discord.Interaction,
            project_id: int,
            environment: str,
            profile: Optional[str] = None,
            key: Optional[str] = None,
            secret: Optional[str] = None,
            region: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            await self.set_project(project_id)

            credentials = await self.process_aws_credentials(
                interaction,
                aws_profile=profile,
                aws_access_key=key,
                aws_secret_key=secret,
                aws_region=region
            )

            if not credentials:
                return

            await self.project_manager.add_aws_environment(
                project_id=project_id,
                environment=environment,
                **credentials
            )

            credential_source = "perfil" if profile else "credenciais customizadas"
            await interaction.followup.send(
                f"✅ Configuração AWS para o projeto {project_id} foi definida com sucesso para o "
                f"ambiente {environment} usando {credential_source} (região: {credentials['aws_region']})",
                ephemeral=True
            )

        except Exception as e:
            self.logger.error(f"Error configuring AWS project: {str(e)}")
            await interaction.followup.send(
                f"❌ Erro ao configurar projeto AWS: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    cog = ProjectCog(bot)
    await bot.add_cog(cog)