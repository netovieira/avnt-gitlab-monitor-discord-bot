import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from gitlab_webhook import setup_webhook, start_webhook
from discord_manager import DiscordManager
from user_link import UserLink
from config import Config
from gitlab import Gitlab
from discord.errors import Forbidden, NotFound

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 5000))
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', 'https://192.168.1.28') 

logger.info(f'<<==============================================================================  START  ==============================================================================>>')
logger.info(f'env: WEBHOOK_PORT: {WEBHOOK_PORT}, WEBHOOK_HOST: {WEBHOOK_HOST}, TOKEN: {TOKEN}')
logger.info(f'<<==============================================================================   END   ==============================================================================>>')

HELP_MESSAGES_CONTENT = [
        """
# 🦖 Saudações, meros mortais! Aqui é o Dino, seu assistente GitLab-Discord supremamente inteligente!

Parece que vocês precisam da minha incomparável sabedoria para entender como esse bot funciona. Muito bem, preparem-se para serem iluminados!

## Comandos Que Vocês Podem Tentar Dominar

### Configuração (Não estraguem tudo!)
• `!config_gitlab <url> <token>`
  Configurem a URL e o token do GitLab. É como amarrar os cadarços, só que para gênios da programação.
  Exemplo: `!config_gitlab https://gitlab.com seu_token_secreto_aqui`
        """,
        """
### Dominando Projetos (Ou Pelo Menos Tentando)
• `!add_project <id>`
  Adicionem um projeto do GitLab à minha vigília onisciente.
  Exemplo: `!add_project 12345`

• `!remove_project <id>`
  Removam um projeto da minha atenção divina. Mas por que vocês fariam isso?
  Exemplo: `!remove_project 12345`

### Configurando Notificações (Para Eu Poder Acordar Vocês às 3 da Manhã)
• `!add_role <função> <email>`
  Associem uma função a um email. É como dar um nome a um pet, só que mais nerd.
  Exemplo: `!add_role desenvolvedor-que-nao-dorme usuario@exemplo.com`
        """,
        """
• `!add_notification <tipo_evento> <função>`
  Configurem quem eu devo importunar e quando.
  Exemplo: `!add_notification merge_request desenvolvedor-que-nao-dorme`

### Informações (Para Os Curiosos e Esquecidos)
• `!show_config`
  Vejam como vocês configuraram tudo. Spoiler: provavelmente não tão bem quanto eu teria feito.

• `!ajuda`
  Invoquem minha presença gloriosa novamente. Sei que vocês sentirão falta da minha voz.

• `!is_running`
  Se eu estiver muito quieto, algo de errado tem! Verifique se estou bem com esse comando.
        """,
        """
## Observações Cruciais (Leiam Isso ou Chorem Depois)
• Todos os comandos, exceto `!ajuda`, exigem permissões de administrador. Não que eu ache que vocês sejam dignos, mas regras são regras.
• As categorias são criadas baseadas nos grupos do GitLab (em MAIÚSCULAS, para os que têm dificuldade de enxergar o óbvio).
• Os canais são nomeados de acordo com o projeto. Não foi ideia minha, eu teria escolhido nomes mais criativos.
• Se houver conflito de nomes, adicionarei um número no final. Considerem isso como minha assinatura artística.

Se ainda tiverem dúvidas (o que é bem provável), chamem o administrador. Ou melhor, tentem resolver sozinhos primeiro. Crescimento pessoal, sabe como é.

Agora, se me dão licença, tenho um universo digital para governar. Dino, o Magnífico, desligando.
        """
]

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
    help_messages = HELP_MESSAGES_CONTENT
    
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
    logger.info('Add project command triggered')
    config = Config()
    
    # Get GitLab configuration
    gitlab_url = await config.get_gitlab_config('url')
    gitlab_token = await config.get_gitlab_config('token')
    
    if not gitlab_url or not gitlab_token:
        await ctx.send("GitLab configuration is not set. Please use !config_gitlab first.")
        return

    # await ctx.user_link.sync_users()

    # Initialize GitLab client
    gl = Gitlab(gitlab_url, private_token=gitlab_token)
    
    # try:
        # Get project details from GitLab
    project = gl.projects.get(project_id)
    project_name = project.name
    
    # Get group name (or use "Other" if no group)
    group_name = project.namespace['name'] if project.namespace['kind'] == 'group' else "OTHER"
    category_name = group_name.upper()

    # Create or get category
    category = discord.utils.get(ctx.guild.categories, name=category_name)
    if not category:
        category = await ctx.guild.create_category(category_name)
        logger.info(f"Created new category: {category_name}")
    else:
        logger.info(f"Using existing category: {category_name}")

    # Create channel
    channel_name = f"{project_name.lower().replace(' ', '-')}"
    
    text_channel = discord.utils.get(ctx.guild.channels, name=channel_name)
    logger.info(f"text_channel: {text_channel}")
    
    if not text_channel:
        await category.create_text_channel(channel_name)
        logger.info(f"Created new text channel: '{channel_name}' in category '{category_name}'")
    
    wr_channel = discord.utils.get(ctx.guild.channels, name=f"WR: {project_name}")
    logger.info(f"wr_channel: {wr_channel}")
    
    if not wr_channel:
        await category.create_voice_channel(f"WR: {project_name}")
        logger.info(f"Created new audio channel: '{project_name} - War Room' in category '{category_name}'")
    
    cr_channel = discord.utils.get(ctx.guild.channels, name=f"CR: {project_name}")
    logger.info(f"cr_channel: {cr_channel}")
    
    if not cr_channel:
        await category.create_voice_channel(f"CR: {project_name}")
        logger.info(f"Created new audio channel: '{project_name} - Code Review' in category '{category_name}'")

    # Add project to configuration
    await config.add_project(project_id, project_name, group_name, channel_name)
    
    # Set up webhook for the project
    webhook_url = f"{WEBHOOK_HOST}/webhook/{project_id}"
    logger.info(f"WEBHOOK_HOST: {WEBHOOK_HOST}")
    logger.info(f"webhook_url: {webhook_url}")

    try:
        response = await project.hooks.create({
            'url': webhook_url,
            'push_events': True,
            'pipeline_events': True,
            'merge_requests_events': True,
            'token': gitlab_token
        })
        logger.info(f"response {response}")

        logger.info(f"Set up webhook for project {project_name}")
    except Exception as e:
        logger.error(f"Failed to create webhook: {str(e)}")
        await ctx.send(f"Failed to set up webhook (url: {webhook_url}): {str(e)}")
    
    await ctx.send(f"Projeto '{project_name}' (ID: {project_id}) adicionado com sucesso! Canal: #{channel_name}")
    # except Exception as e:
    #     logger.error(f"Error adding project: {str(e)}")
    #     await ctx.send(f"Ocorreu um erro ao adicionar o projeto: {str(e)}")

@bot.command(name='remove_project')
@commands.has_permissions(administrator=True)
async def remove_project(ctx, project_id: int):
    logger.info(f'Remove project command triggered for project ID: {project_id}')
    config = Config()
    
    # Get GitLab configuration
    gitlab_url = await config.get_gitlab_config('url')
    gitlab_token = await config.get_gitlab_config('token')
    
    if not gitlab_url or not gitlab_token:
        await ctx.send("GitLab configuration is not set. Please use !config_gitlab first.")
        return

    # Initialize GitLab client
    gl = Gitlab(gitlab_url, private_token=gitlab_token)
    
    try:
        # Get project details from configuration
        project_info = await config.get_project(project_id)
        if not project_info:
            await ctx.send(f"Project with ID {project_id} not found in the configuration.")
            return

        project_name, group_name, channel_name = project_info[1:]

        # Remove project from configuration
        await config.remove_project(project_id)
        
        # Remove Discord channel
        category = discord.utils.get(ctx.guild.categories, name=group_name.upper())
        if category:
            channel = discord.utils.get(category.channels, name=channel_name)
            if channel:
                await channel.delete()
                logger.info(f"Deleted channel: {channel_name}")
        
        # Remove GitLab webhook
        project = gl.projects.get(project_id)
        webhooks = project.hooks.list()
        for hook in webhooks:
            if hook.url.endswith(f"/webhook/{project_id}"):
                project.hooks.delete(hook.id)
                logger.info(f"Removed webhook for project {project_name}")
                break
        
        await ctx.send(f"Projeto '{project_name}' (ID: {project_id}) removido com sucesso!")
    except Exception as e:
        logger.error(f"Error removing project: {str(e)}")
        await ctx.send(f"Ocorreu um erro ao remover o projeto: {str(e)}")
        
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