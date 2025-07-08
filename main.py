import os
import asyncio
import discord
from discord.ext import commands
from discord.channel import ForumChannel
from core.db.project import Project
from core.env import TOKEN, WEBHOOK_PORT
from core.logger import getLogger
from gitlab_webhook import setup_webhook, start_webhook
from discord_manager import DiscordManager
from user_link import UserLink
from Config import Config
import random
import datetime

# Set up logging
logger = getLogger('discord')


class GinoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )

        # Configurações do bot
        self.config = Config()
        self.project_messages = {}
        self.projects = {
            "Project A": {"status": ["On Track", "Delayed", "Ahead"], "tasks": range(10, 51)},
            "Project B": {"status": ["In Progress", "On Hold", "Completed"], "tasks": range(5, 31)},
            "Project C": {"status": ["Planning", "Executing", "Reviewing"], "tasks": range(15, 41)}
        }
        self.ANNOUNCEMENT_CHANNEL_ID = 1291829032589066300
        self.synced = False

    async def setup_hook(self):
        """Configurações iniciais do bot"""
        try:
            # Inicializa o banco de dados
            config = Project()
            await config.initialize()

            # Inicializa gerenciadores
            self.discord_manager = DiscordManager(self)
            self.user_link = UserLink()
            self.user_link.set_bot(self)

            # Configura webhook
            runner, port = setup_webhook(
                self,
                self.discord_manager,
                self.user_link,
                config,
                WEBHOOK_PORT
            )
            await start_webhook(runner, port)
            logger.info(f'Webhook server started on port {port}')

            # Carrega extensões
            await self.load_all_extensions()

            logger.info("Bot setup completed successfully!")

        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            raise

    async def load_all_extensions(self):
        """Carrega todas as extensões/cogs"""
        cogs_to_load = [
            'cogs.dashboard',
            'cogs.aws_resources',
            'cogs.registration',
            'cogs.project',
            'cogs.admin_commands',
            'core.cogs.server_management_cog'
        ]

        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded extension: {cog}")
            except Exception as e:
                logger.error(f"Failed to load extension {cog}: {e}")

    async def on_ready(self):
        """Evento quando o bot está pronto"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')

        # Sincroniza slash commands apenas uma vez
        if not self.synced:
            try:
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} command(s)")
                self.synced = True
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")

    async def on_message(self, message):
        """Evento para processar mensagens"""
        if message.author == self.user:
            return

        logger.info(f'📨 Message received: {message.content}')

        # Processa comandos prefix
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        """Tratamento global de erros de comandos prefix"""
        if isinstance(error, commands.CommandNotFound):
            # Ignora comandos não encontrados silenciosamente
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Você não tem permissão para usar este comando!")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Argumento obrigatório ausente: `{error.param.name}`")
            return

        logger.error(f"Command error in {ctx.command}: {error}")
        await ctx.send(f"❌ Erro ao executar comando: {str(error)}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Tratamento global de erros de slash commands"""
        if isinstance(error, discord.app_commands.CheckFailure):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando!",
                ephemeral=True
            )
            return

        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Você não tem as permissões necessárias!",
                ephemeral=True
            )
            return

        logger.error(f"App command error in {interaction.command}: {error}")

        # Tenta responder ao usuário
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Erro ao executar comando: {str(error)}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Erro ao executar comando: {str(error)}",
                    ephemeral=True
                )
        except:
            pass

    # Comandos prefix básicos para compatibilidade
    @commands.command(name='help', aliases=['ajuda'])
    async def help_command(self, ctx):
        """Comando de ajuda básico"""
        embed = discord.Embed(
            title="🦖 Gino - O Bot Supremo",
            description="Use `/help` para ver todos os comandos disponíveis!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Comandos Principais",
            value="• `/register_project` - Registrar projeto\n• `/configure_project` - Configurar projeto\n• `/list_projects` - Listar projetos",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name='sync')
    @commands.has_permissions(administrator=True)
    async def sync_commands(self, ctx):
        """Sincroniza slash commands manualmente"""
        try:
            synced = await self.tree.sync()
            await ctx.send(f"✅ Sincronizados {len(synced)} comando(s)!")
            logger.info(f"Manually synced {len(synced)} command(s)")
        except Exception as e:
            await ctx.send(f"❌ Erro ao sincronizar: {str(e)}")
            logger.error(f"Manual sync failed: {e}")

    @commands.command(name='status')
    async def status_command(self, ctx):
        """Verifica o status do bot"""
        embed = discord.Embed(
            title="🦖 Status do Gino",
            color=discord.Color.green()
        )
        embed.add_field(name="Latência", value=f"{round(self.latency * 1000)}ms", inline=True)
        embed.add_field(name="Servidores", value=str(len(self.guilds)), inline=True)
        embed.add_field(name="Usuários", value=str(len(self.users)), inline=True)
        await ctx.send(embed=embed)


async def main():
    """Função principal para iniciar o bot"""
    try:
        async with GinoBot() as bot:
            await bot.start(TOKEN)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")