import logging
from aiohttp import web
import discord
from discord_manager import DiscordManager
from user_link import UserLink
from notification_templates import get_notification_message
from Config import Config
from actions.project import Project

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

async def handle_webhook(request, bot, discord_manager, user_link, config):
    project_id = int(request.match_info.get('project_id'))
    data = await request.json()
    event_type = request.headers.get('X-Gitlab-Event')

    project_info = await config.get_project(project_id)
    if not project_info:
        return web.Response(text='Project not found', status=404)

    # Unpack project_info, assuming the order of columns in your database
    id, name, group_name, channel_name = project_info

    # Get the first guild (assuming the bot is in only one guild)
    guild = bot.guilds[0] if bot.guilds else None
    if not guild:
        return web.Response(text='Bot is not in any guild', status=500)

    # Find the category and channel
    category = discord.utils.get(guild.categories, name=group_name)
    if not category:
        return web.Response(text=f'Category "{group_name}" not found', status=404)
    
    channel = discord.utils.get(category.channels, name=channel_name)
    if not channel:
        return web.Response(text=f'Channel "{channel_name}" not found in category "{group_name}"', status=404)

    logger.info(f'event_type: {event_type}')
    logger.info(f'data: {data}')

    # Create a Project instance
    project = Project(guild)
    await project.load(project_id)

    # Call the handle_webhook method of the Project instance
    await project.handle_webhook(bot, data, event_type)

    return web.Response(text='Webhook received and processed')

async def handle_push(data, channel, user_link, config):
    branch = data['ref'].split('/')[-1]
    commits = data['commits']

    message = get_notification_message('push', branch=branch, commit_count=len(commits))

    # Fetch notifications from the database
    notifications = await config.get_notifications()
    roles_to_notify = [role for event_type, role in notifications if event_type == 'push']
    
    mentions = await user_link.get_mention_string(roles_to_notify)

    await channel.send(f"{mentions}\n{message}")


async def handle_merge_request(data, channel, user_link, config):
    mr_action = data['object_attributes']['state']
    mr_title = data['object_attributes']['title']
    mr_description = data['object_attributes']['description']
    mr_url = data['object_attributes']['url']
    author_name = data['object_attributes']['last_commit']['author']['name']
    source_branch = data['object_attributes']['source_branch']
    target_branch = data['object_attributes']['target_branch']
    merge_status = data['object_attributes']['merge_status']
    merge_error = data['object_attributes']['merge_error']
    created_at = data['object_attributes']['created_at']
    last_edited_at = data['object_attributes']['last_edited_at']

    message = get_notification_message(
        'merge_request', mr_action, 
        title=mr_title, 
        description=mr_description, 
        url=mr_url, 
        author=author_name, 
        source=source_branch, 
        target=target_branch,
        merge_status=merge_status,
        merge_error=merge_error,
        created_at=created_at,
        last_edited_at=last_edited_at
    )

    logger.info(message)
    await channel.send(f"{message}")


async def handle_issue(data, channel, user_link, config):
    issue_action = data['object_attributes']['action']
    issue_title = data['object_attributes']['title']
    issue_url = data['object_attributes']['url']

    message = get_notification_message('issue', issue_action, title=issue_title, url=issue_url)

    # Fetch notifications from the database
    notifications = await config.get_notifications()
    roles_to_notify = [role for event_type, role in notifications if event_type == 'issue']
    
    mentions = await user_link.get_mention_string(roles_to_notify)

    await channel.send(f"{mentions}\n{message}")

async def handle_pipeline(data, channel, user_link, config):
    pipeline_status = data['object_attributes']['status']
    branch = data['object_attributes']['ref']

    message = get_notification_message('pipeline', pipeline_status, branch=branch)

    # Fetch notifications from the database
    notifications = await config.get_notifications()
    roles_to_notify = [role for event_type, role in notifications if event_type == 'pipeline']
    
    mentions = await user_link.get_mention_string(roles_to_notify)

    await channel.send(f"{mentions}\n{message}")


def setup_webhook(bot, discord_manager, user_link, config, port):
    app = web.Application()
    app.router.add_post('/webhook/{project_id}', lambda request: handle_webhook(request, bot, discord_manager, user_link, config))
    
    runner = web.AppRunner(app)
    return runner, port

async def start_webhook(runner, port):
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f'Webhook server started on port {port}')