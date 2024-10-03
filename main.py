import os
import asyncio
import discord
from discord.ext import commands
from actions.project import Project
from core.env import TOKEN, WEBHOOK_PORT
from core.logger import getLogger
from gitlab_webhook import setup_webhook, start_webhook
from discord_manager import DiscordManager
from helpers.messages import HELP_MESSAGE_CONTENT
from user_link import UserLink
from config import Config

# Set up logging
logger = getLogger('discord')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    config = Config()
    discord_manager = DiscordManager(bot)
    user_link = UserLink(config=config)
    user_link.set_bot(bot)
    
    runner, port = setup_webhook(bot, discord_manager, user_link, config, WEBHOOK_PORT)
    await start_webhook(runner, port)
    logger.info(f'Webhook server started on port {port}')


@bot.event
async def on_message(message):
    logger.info(f'Message received: {message.content}')
    await bot.process_commands(message)

@bot.command(name='is_running')
async def test(ctx):
    logger.info('is_running command triggered')
    await ctx.send('O bot está funcionando!')
        
@bot.command(name='ajuda')
async def help_command(ctx):
    logger.info('Comando de ajuda acionado')
    help_messages = HELP_MESSAGE_CONTENT
    
    for message in help_messages:
        await ctx.send(message)

@bot.command(name='config_gitlab')
@commands.has_permissions(administrator=True)
async def config_gitlab(ctx, url: str, token: str):
    logger.info('Config GitLab command triggered')
    config = Config()
    await config.set_gitlab_config('url', url)
    await config.set_gitlab_config('token', token)
    await ctx.send("Configuração do GitLab atualizada com sucesso!")

@bot.command(name='add_project')
@commands.has_permissions(administrator=True)
async def add_project(ctx, project_id: int):
    project = Project(ctx)
    await project.add(project_id)

    await ctx.send(f"Projeto {project_id} adicionado com sucesso!")
    logger.info(f'Projeto {project_id} adicionado com sucesso')

@bot.command(name='remove_project')
@commands.has_permissions(administrator=True)
async def remove_project(ctx, project_id: int):
    project = Project(ctx)
    await project.load(project_id)
    await project.remove()
    
    await ctx.send(f"Projeto {project_id} removido com sucesso!")
    logger.info(f'Projeto {project_id} removido com sucesso')
        
@bot.command(name='add_role')
@commands.has_permissions(administrator=True)
async def add_role(ctx, role: str, email: str):
    logger.info('Add role command triggered')
    config = Config()
    await config.add_role(role, email)
    await ctx.send(f"Função '{role}' associada ao email '{email}' com sucesso!")

@bot.command(name='add_notification')
@commands.has_permissions(administrator=True)
async def add_notification(ctx, event_type: str, role: str):
    logger.info('Add notification command triggered')
    config = Config()
    await config.add_notification(event_type, role)
    await ctx.send(f"Notificação para evento '{event_type}' configurada para a função '{role}' com sucesso!")

@bot.command(name='show_config')
@commands.has_permissions(administrator=True)
async def show_config(ctx):
    logger.info('Show config command triggered')
    config = Config()
    gitlab_url = await config.get_gitlab_config('url')
    projects = await config.get_projects()
    roles = await config.get_roles()
    notifications = await config.get_notifications()

    config_message = "Configuração atual do bot:\n\n"
    config_message += f"GitLab URL: {gitlab_url}\n\n"
    
    logger.info(f'projects: {projects}')

    config_message += "Projetos:\n"
    for project in projects:
        project_id, project_name, project_group, *other_values = project
        config_message += f"- {project_group.upper()} > {project_name}\n"

    
    config_message += "\nFunções:\n"
    for role, email in roles:
        config_message += f"- {role}: {email}\n"
    
    config_message += "\nNotificações:\n"
    for event_type, role in notifications:
        config_message += f"- {event_type}: {role}\n"

    await ctx.send(config_message)

async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())