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

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    config = Project()
    await config.initialize()
    
    discord_manager = DiscordManager(bot)
    user_link = UserLink()
    user_link.set_bot(bot)
    
    runner, port = setup_webhook(bot, discord_manager, user_link, config, WEBHOOK_PORT)
    await start_webhook(runner, port)
    logger.info('\n\n\n\n\n\n\n\n\n\n\n\n\n')
    logger.info(f'Webhook server started on port {port}')

    # Carregando as cogs
    await load_extensions(bot)


async def load_extension(bot, cogName):
    try:
        await bot.load_extension(cogName)
        logger.info(f"Successfully loaded extension: {cogName}")
    except Exception as e:
        logger.error(f"Failed to load extension {cogName}: {str(e)}")

async def load_extensions(bot):
    db_dir = os.path.join(os.path.dirname(__file__), 'cogs')
    for filename in os.listdir(db_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = f'cogs.{filename[:-3]}'
            await load_extension(bot, module_name)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    logger.info(f'Message received: {message.content}')
    await bot.process_commands(message)


# Store message IDs for each project
project_messages = {}

# Simulated data for projects
projects = {
    "Project A": {"status": ["On Track", "Delayed", "Ahead"], "tasks": range(10, 51)},
    "Project B": {"status": ["In Progress", "On Hold", "Completed"], "tasks": range(5, 31)},
    "Project C": {"status": ["Planning", "Executing", "Reviewing"], "tasks": range(15, 41)}
}

# Replace this with your actual announcement channel ID
ANNOUNCEMENT_CHANNEL_ID = 1291829032589066300 

async def create_dashboard(client):
    channel = client.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if channel is None:
        logger.error(f"Could not find channel with ID {ANNOUNCEMENT_CHANNEL_ID}")
        return

    if isinstance(channel, ForumChannel):
        logger.info("The specified channel is a Forum Channel. Creating a thread for the dashboard.")
        # Create a new thread for each project
        for project in projects:
            try:
                thread = await channel.create_thread(
                    name=f"{project} Dashboard",
                    content=f"Dashboard for {project}",
                    auto_archive_duration=10080  # Set to 7 days
                )
                project_messages[project] = (thread.id, thread.message.id)
            except discord.errors.Forbidden:
                logger.error(f"Bot doesn't have permission to create threads in channel {ANNOUNCEMENT_CHANNEL_ID}")
                return
            except Exception as e:
                logger.error(f"Error creating dashboard thread for {project}: {str(e)}")
    else:
        # Original logic for non-forum channels
        for project in projects:
            try:
                message = await channel.send(f"Loading data for {project}...")
                project_messages[project] = message.id
            except discord.errors.Forbidden:
                logger.error(f"Bot doesn't have permission to send messages in channel {ANNOUNCEMENT_CHANNEL_ID}")
                return
            except Exception as e:
                logger.error(f"Error creating dashboard for {project}: {str(e)}")

@tasks.loop(minutes=1)
async def update_dashboard():
    channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if channel is None:
        logger.error(f"Could not find channel with ID {ANNOUNCEMENT_CHANNEL_ID}")
        return

    is_forum = isinstance(channel, ForumChannel)

    for project, message_info in project_messages.items():
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
            logger.error(f"Message for {project} not found. Recreating...")
            if is_forum:
                thread = await channel.create_thread(
                    name=f"{project} Dashboard",
                    content=f"Recreating dashboard for {project}...",
                    auto_archive_duration=10080
                )
                project_messages[project] = (thread.id, thread.message.id)
            else:
                new_message = await channel.send(f"Recreating data for {project}...")
                project_messages[project] = new_message.id
        except Exception as e:
            logger.error(f"Error updating dashboard for {project}: {str(e)}")

@bot.command(name='testex')
@commands.has_permissions(administrator=True)
async def test_join(ctx):
    registration_cog = bot.get_cog('Registration')
    if registration_cog:
        await registration_cog.start_registration(ctx.author)
    else:
        await ctx.send("Erro: Cog de registro não encontrado.")

@bot.command(name='is_running')
async def test(ctx):
    logger.info('is_running command triggered')
    await ctx.send('O bot está funcionando! Gino, o Magnífico, está aqui para servir... ou talvez para dominar o mundo. Quem sabe?')

@bot.command(name='criar_dashboard2')
async def criar_dashboard(ctx, categoria):
    # Criar um embed para a dashboard
    embed = discord.Embed(
        title=f"Dashboard - {categoria}",
        description="Informações do projeto",
        color=discord.Color.blue()
    )

    # Exibir informações falsas sobre o repositório
    embed.add_field(name="Repositório Git", value="Nome do Repositório", inline=False)
    embed.add_field(name="Data da Última Atualização", value="01/10/2024", inline=True)
    embed.add_field(name="Data do Último Deploy", value="01/10/2024", inline=True)

    # Botões para forçar deploy e atualização
    view = discord.ui.View()
    deploy_button = discord.ui.Button(label="Forçar Deploy", style=discord.ButtonStyle.green)
    update_button = discord.ui.Button(label="Atualizar Informações", style=discord.ButtonStyle.blurple)

    # Definindo a ação dos botões
    async def deploy_callback(interaction):
        await interaction.response.send_message("Deploy forçado!", ephemeral=True)

    async def update_callback(interaction):
        await interaction.response.send_message("Informações atualizadas!", ephemeral=True)

    deploy_button.callback = deploy_callback
    update_button.callback = update_callback

    view.add_item(deploy_button)
    view.add_item(update_button)

    # Adicionando o gráfico (usando um link de exemplo)
    embed.add_field(name="Gráfico de Acessos/Hora", value="[Gráfico Aqui](https://example.com)", inline=False)
    embed.add_field(name="Uso de Recursos", value="🔋 75% de uso", inline=False)  # Exemplo de medidor

    # Enviar o embed no canal
    await ctx.send(embed=embed, view=view)

# Função para lidar com o botão de deploy
@bot.event
async def on_interaction(interaction):
    if interaction.custom_id == "botao_deploy":
        await interaction.response.send_message("Deploy iniciado para o projeto!", ephemeral=True)
    elif interaction.custom_id == "botao_update":
        await interaction.response.send_message("Atualizando a dashboard...", ephemeral=True)
        # Aqui você pode atualizar o embed ou dados da dashboard com novas informações


async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())