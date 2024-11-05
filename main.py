import os
import asyncio
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
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
            intents=intents
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
            
            # Inicia tarefas em loop
            self.update_dashboard.start()
            
            logger.info("Bot setup completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            raise

    async def load_all_extensions(self):
        """Carrega todas as extensões/cogs"""
        cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f"Loaded extension: cogs.{filename[:-3]}")
                except Exception as e:
                    logger.error(f"Failed to load extension {filename}: {e}")

    @tasks.loop(minutes=1)
    async def update_dashboard(self):
        """Atualiza o dashboard periodicamente"""
        channel = self.get_channel(self.ANNOUNCEMENT_CHANNEL_ID)
        if not channel:
            logger.error(f"Could not find channel {self.ANNOUNCEMENT_CHANNEL_ID}")
            return

        is_forum = isinstance(channel, ForumChannel)

        for project, message_info in self.project_messages.items():
            try:
                status = random.choice(self.projects[project]["status"])
                tasks_completed = random.choice(self.projects[project]["tasks"])
                
                embed = discord.Embed(
                    title=f"{project} Status",
                    color=discord.Color.green()
                )
                embed.add_field(name="Status", value=status, inline=False)
                embed.add_field(name="Tasks Completed", value=str(tasks_completed), inline=False)
                embed.set_footer(text=f"Last updated: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                
                if is_forum:
                    thread_id, message_id = message_info
                    thread = await channel.fetch_thread(thread_id)
                    message = await thread.fetch_message(message_id)
                else:
                    message = await channel.fetch_message(message_info)
                
                await message.edit(content="", embed=embed)
                
            except discord.NotFound:
                logger.warning(f"Message for {project} not found, recreating...")
                await self.recreate_dashboard_message(channel, project, is_forum)
            except Exception as e:
                logger.error(f"Error updating dashboard for {project}: {e}")

    async def recreate_dashboard_message(self, channel, project, is_forum):
        """Recria mensagem do dashboard se foi deletada"""
        try:
            if is_forum:
                thread = await channel.create_thread(
                    name=f"{project} Dashboard",
                    content=f"Dashboard for {project}",
                    auto_archive_duration=10080
                )
                self.project_messages[project] = (thread.id, thread.message.id)
            else:
                message = await channel.send(f"Loading data for {project}...")
                self.project_messages[project] = message.id
        except Exception as e:
            logger.error(f"Error recreating dashboard message: {e}")

    async def on_ready(self):
        """Evento quando o bot está pronto"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
    async def on_message(self, message):
        """Evento para processar mensagens"""
        if message.author == self.user:
            return
            
        logger.info(f'Message received: {message.content}')
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        """Tratamento global de erros de comandos"""
        if isinstance(error, commands.CommandNotFound):
            return
            
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Você não tem permissão para usar este comando!")
            return
            
        logger.error(f"Command error: {error}")
        await ctx.send(f"Erro ao executar comando: {str(error)}")

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