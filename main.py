import os
import asyncio
import discord
from discord.ext import tasks
from discord.channel import ForumChannel
from discord import app_commands

from Config import Config
from core.db.project import Project
from core.env import TOKEN, WEBHOOK_PORT
from core.logger import getLogger
from gitlab_webhook import setup_webhook, start_webhook
from discord_manager import DiscordManager
from user_link import UserLink
import random
import datetime

# Logging
logger = getLogger('discord')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True


class GinoBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.project_messages = {}

    async def setup_hook(self):
        try:
            await self.load_cogs()

            guild_id = 1390760661730070628  # servidor de testes
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Sincronizados {len(synced)} comandos slash no servidor {guild_id}")
        except Exception as e:
            logger.error(f"Erro ao sincronizar comandos slash: {e}")

    async def load_cogs(self):
        import importlib

        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                module_name = f'cogs.{filename[:-3]}'
                module = importlib.import_module(module_name)
                if hasattr(module, 'setup'):
                    await module.setup(self)


bot = GinoBot()

# ========== Eventos ==========
@bot.event
async def on_ready():
    logger.info(f'{bot.user} conectado com sucesso!')
    logger.info(f'Guilds: {len(bot.guilds)}')

    config = Config()
    await config.initialize()

    discord_manager = DiscordManager(bot)
    user_link = UserLink()
    user_link.set_bot(bot)

    runner, port = setup_webhook(bot, discord_manager, user_link, config, WEBHOOK_PORT)
    await start_webhook(runner, port)
    logger.info(f"Webhook server started on port {port}")


@bot.event
async def on_interaction(interaction: discord.Interaction):
    # Componente (botão, select etc.)
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id")
        if custom_id == "botao_deploy":
            await interaction.response.send_message("Deploy iniciado para o projeto!", ephemeral=True)
        elif custom_id == "botao_update":
            await interaction.response.send_message("Atualizando a dashboard...", ephemeral=True)


# ========== Comandos Slash ==========
@bot.tree.command(name="testex", description="Inicia o processo de registro (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def testex(interaction: discord.Interaction):
    registration_cog = bot.get_cog('Registration')
    if registration_cog:
        await registration_cog.start_registration(interaction.user)
        await interaction.response.send_message("Registro iniciado com sucesso!", ephemeral=True)
    else:
        await interaction.response.send_message("Erro: Cog de registro não encontrado.", ephemeral=True)


@bot.tree.command(name="is_running", description="Verifica se o bot está funcionando")
async def is_running(interaction: discord.Interaction):
    logger.info('Comando /is_running executado')
    await interaction.response.send_message(
        'O bot está funcionando! Gino, o Magnífico, está aqui para servir... ou talvez para dominar o mundo. Quem sabe?',
        ephemeral=True
    )


@bot.tree.command(name="criar_dashboard2", description="Cria um dashboard de exemplo com botões")
@app_commands.describe(categoria="Nome da categoria ou projeto")
async def criar_dashboard2(interaction: discord.Interaction, categoria: str):
    embed = discord.Embed(
        title=f"Dashboard - {categoria}",
        description="Informações do projeto",
        color=discord.Color.blue()
    )

    embed.add_field(name="Repositório Git", value="Nome do Repositório", inline=False)
    embed.add_field(name="Data da Última Atualização", value="01/10/2024", inline=True)
    embed.add_field(name="Data do Último Deploy", value="01/10/2024", inline=True)
    embed.add_field(name="Gráfico de Acessos/Hora", value="[Gráfico Aqui](https://example.com)", inline=False)
    embed.add_field(name="Uso de Recursos", value="🔋 75% de uso", inline=False)

    view = discord.ui.View()

    deploy_button = discord.ui.Button(label="Forçar Deploy", style=discord.ButtonStyle.green, custom_id="botao_deploy")
    update_button = discord.ui.Button(label="Atualizar Informações", style=discord.ButtonStyle.blurple, custom_id="botao_update")

    view.add_item(deploy_button)
    view.add_item(update_button)

    await interaction.response.send_message(embed=embed, view=view)


# ========== Funções auxiliares ==========
async def load_extensions(bot):
    import traceback

    db_dir = os.path.join(os.path.dirname(__file__), 'cogs')
    for filename in os.listdir(db_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = f'cogs.{filename[:-3]}'
            try:
                await bot.load_extension(module_name)
                logger.info(f"Loaded extension: {module_name}")
            except Exception as e:
                logger.error(f"Erro ao carregar {module_name}: {e}")
                traceback.print_exc()


# ========== Dashboard simulada ==========
ANNOUNCEMENT_CHANNEL_ID = 1291829032589066300

projects = {
    "Project A": {"status": ["On Track", "Delayed", "Ahead"], "tasks": range(10, 51)},
    "Project B": {"status": ["In Progress", "On Hold", "Completed"], "tasks": range(5, 31)},
    "Project C": {"status": ["Planning", "Executing", "Reviewing"], "tasks": range(15, 41)}
}


async def create_dashboard(client):
    channel = client.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if channel is None:
        logger.error(f"Could not find channel with ID {ANNOUNCEMENT_CHANNEL_ID}")
        return

    if isinstance(channel, ForumChannel):
        logger.info("Canal é um ForumChannel, criando threads.")
        for project in projects:
            try:
                thread = await channel.create_thread(
                    name=f"{project} Dashboard",
                    content=f"Dashboard for {project}",
                    auto_archive_duration=10080
                )
                bot.project_messages[project] = (thread.id, thread.message.id)
            except Exception as e:
                logger.error(f"Erro ao criar thread para {project}: {str(e)}")
    else:
        for project in projects:
            try:
                message = await channel.send(f"Loading data for {project}...")
                bot.project_messages[project] = message.id
            except Exception as e:
                logger.error(f"Erro ao criar dashboard para {project}: {str(e)}")


@tasks.loop(minutes=1)
async def update_dashboard():
    channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if channel is None:
        logger.error(f"Could not find channel with ID {ANNOUNCEMENT_CHANNEL_ID}")
        return

    is_forum = isinstance(channel, ForumChannel)

    for project, message_info in bot.project_messages.items():
        try:
            status = random.choice(projects[project]["status"])
            tasks_completed = random.choice(projects[project]["tasks"])

            embed = discord.Embed(title=f"{project} Status", color=0x00ff00)
            embed.add_field(name="Status", value=status, inline=False)
            embed.add_field(name="Tasks Completed", value=f"{tasks_completed}", inline=False)
            embed.set_footer(text=f"Last updated: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

            if is_forum:
                thread_id, message_id = message_info
                thread = await channel.fetch_thread(thread_id)
                message = await thread.fetch_message(message_id)
            else:
                message = await channel.fetch_message(message_info)

            await message.edit(content="", embed=embed)
        except discord.errors.NotFound:
            logger.error(f"Mensagem de {project} não encontrada. Recriando...")
        except Exception as e:
            logger.error(f"Erro ao atualizar {project}: {str(e)}")


# ========== Start ==========
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
