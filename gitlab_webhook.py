import logging
from aiohttp import web
import discord
import asyncio
from discord_manager import DiscordManager
from user_link import UserLink
from notification_templates import get_notification_message
from config import Config

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

    _, project_name, group_name, channel_name = project_info

    channel = discord.utils.get(bot.get_all_channels(), name=channel_name)
    if not channel:
        return web.Response(text='Channel not found', status=404)

    logger.info(f'event_type: {event_type}')
    logger.info(f'data: {data}')

    event_handlers = {
        'Push Hook': handle_push,
        'Merge Request Hook': handle_merge_request,
        'Issue Hook': handle_issue,
        'Pipeline Hook': handle_pipeline
    }

    handler = event_handlers.get(event_type)
    if handler:
        await handler(data, channel, user_link, config)
    else:
        logger.warning(f'Unhandled event type: {event_type}')

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
    mr_url = data['object_attributes']['url']
    author_name = data['user']['name']
    source_branch = data['object_attributes']['source_branch']
    target_branch = data['object_attributes']['target_branch']

    message = get_notification_message(
        'merge_request', mr_action, 
        title=mr_title, 
        url=mr_url, 
        author=author_name, 
        source=source_branch, 
        target=target_branch
    )

    # Fetch notifications from the database
    notifications = await config.get_notifications()
    roles_to_notify = [role for event_type, role in notifications if event_type == 'merge_request']
    
    mentions = await user_link.get_mention_string(roles_to_notify)

    await channel.send(f"{mentions}\n{message}")


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