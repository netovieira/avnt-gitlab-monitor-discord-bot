import re
import asyncio

from discord.ui import Button, View
from Config import Config
from core.discord import Discord
from core.env import WEBHOOK_HOST
from core.logger import getLogger
from helpers.gitlab import GitlabClient
from notification_templates import get_notification_message
from user_link import UserLink

# Set up logging
logger = getLogger('discord-actions:project')


class Project:

    guild = None;
    last_id:int = -1;
    project = None;
    config = None;
    gl = None;
    discord = None;

    category_name = None;
    notification_channel_name = None;

    category = None;
    notification_channel = None;
    war_room_channel = None;
    code_review_channel = None;

    projectSettings = None;

    def __init__(self, guild):
        self.config = Config()
        self.guild = guild;
        self.discord = Discord(guild);
    

    async def load(self, project_id, force=True):
        
        if self.gl is None:
            self.gl = await  GitlabClient.create();
        
        if self.last_id == project_id and not force:
            return self;
    
        project =  self.gl.instance.projects.get(project_id)
        if not project:
            raise Exception(f"Project with ID {project_id} not found.")
            return

        # Set Project and Discord properties 
        self.project = project

        class DotDict:
            def __init__(self, dictionary):
                for key, value in dictionary.items():
                    setattr(self, key, value)

        _ = await self.config.get_project(project_id)
        self.projectSettings = DotDict({
            "id": _[0],
            "name": _[1],
            "group_name": _[2],
            "channel_name": _[3]
        });
        
        self.category_name = (self.project.namespace['name'] if self.project.namespace['kind'] == 'group' else "OTHER").upper()
        self.notification_channel_name = self.projectSettings.channel_name
        
        self.category = await self.discord.getCategory(self.category_name);
        self.notification_channel = await self.discord.getChannel(self.notification_channel_name);
        self.war_room_channel = await self.discord.getChannel("WAR ROOM", self.category);
        self.code_review_channel = await self.discord.getChannel("CODE REVIEW", self.category);

        return self;

    async def setupDiscord(self):
        logger.info(f"--------------------------------------------------- setupDiscord ---------------------------------------------------")
        if self.category is None:
            self.category = await self.discord.addCategory(self.category_name)
            await self.discord.addVoiceChannel("WAR ROOM", self.category_name)
            await self.discord.addVoiceChannel("CODE REVIEW", self.category_name)

        if not self.notification_channel:
            self.notification_channel = await self.discord.addTextChannel(self.notification_channel_name, self.category_name)

    async def updateConfig(self):
        logger.info(f"--------------------------------------------------- updateConfig ---------------------------------------------------")
        # Add project to configuration    
        if self.projectSettings is None:
            await self.config.add_project(self.project.id, self.project.name, self.category_name);
            self.projectSettings = await self.config.get_project(self.project.id);

    async def setupGitlab(self):
        logger.info(f"--------------------------------------------------- setupGitlab ---------------------------------------------------")
        # Set up webhook for the project
        webhook_url = f"{WEBHOOK_HOST}/webhook/{self.project.id}"
        logger.info(f"WEBHOOK_HOST: {WEBHOOK_HOST}")
        logger.info(f"webhook_url: {webhook_url}")

        try:
            # Verificar se já existe um webhook com a mesma URL
            existing_hooks = await asyncio.to_thread(self.project.hooks.list)
            for hook in existing_hooks:
                if hook.url == webhook_url:
                    logger.info(f"Webhook already exists for URL: {webhook_url}")
                    return  # Sai da função se o webhook já existir

            self.project.hooks.create({
                'url': webhook_url,
                'push_events': True,
                'pipeline_events': True,
                'merge_requests_events': True,
                'token': self.gl.token,
                'enable_ssl_verification': False
            })

            logger.info(f"Set up webhook for project {self.project.name}")
        except Exception as e:
            logger.error(f"Failed to create webhook: {str(e)}")
            raise Exception(f"Failed to set up webhook (url: {webhook_url}): {str(e)}")

    async def add(self, project_id: int = None):
        logger.info('Add project command triggered')
        
        if project_id:
            await self.load(project_id)

        if self.project:

            await self.setupDiscord();
            await self.setupGitlab();

            await self.updateConfig();

    async def remove(self):
        logger.info(f'Remove project command triggered for project ID: {self.project.id}')

        if self.project and self.projectSettings:
            self.config.remove_project(self.project.id)
            self.discord.removeCategory(self.category_name)
        
        webhooks = self.project.hooks.list()
        for hook in webhooks:
            if hook.url.endswith(f"/webhook/{self.project.id}"):
                self.project.hooks.delete(hook.id)
                logger.info(f"Removed webhook for project {self.project.name}")
                break


    async def handle_webhook(self, bot, data, event_type):
        if event_type == 'Merge Request Hook':
            await self.handle_merge_request(bot, data)
        elif event_type == 'Push Hook':
            await self.handle_push(data)
        elif event_type == 'Issue Hook':
            await self.handle_issue(data)
        elif event_type == 'Pipeline Hook':
            await self.handle_pipeline(data)
        else:
            logger.warning(f"Unhandled event type: {event_type}")

    async def handle_merge_request(self, bot, data):
        author_name = data['object_attributes']['last_commit']['author']['name']
        author_email = data['object_attributes']['last_commit']['author']['email']

        mr_action = data['object_attributes']['state']
        mr_title = data['object_attributes']['title']
        mr_description = data['object_attributes']['description']
        mr_url = data['object_attributes']['url']
        source_branch = data['object_attributes']['source_branch']
        target_branch = data['object_attributes']['target_branch']
        merge_status = data['object_attributes']['merge_status']
        merge_error = data['object_attributes']['merge_error']
        created_at = data['object_attributes']['created_at']
        last_edited_at = data['object_attributes']['last_edited_at']

        discord_member = await self.find_discord_member(bot, author_email)
        author_mention = discord_member.mention if discord_member else author_name

        message = get_notification_message(
            'merge_request', mr_action, 
            title=mr_title, 
            description=mr_description, 
            url=mr_url, 
            author=author_mention, 
            source=source_branch, 
            target=target_branch,
            merge_status=merge_status,
            merge_error=merge_error,
            created_at=created_at,
            last_edited_at=last_edited_at
        )


        await self.notification_channel.send(message)
        
        if mr_url:
            button = Button(label="Mais informações", url=mr_url)
            view = View()
            view.add_item(button)
            await self.notification_channel.send(view=view)

    async def handle_push(self, data):
        # Implementar lógica para lidar com eventos de push
        pass

    async def handle_issue(self, data):
        # Implementar lógica para lidar com eventos de issue
        pass

    async def handle_pipeline(self, data):
        # Implementar lógica para lidar com eventos de pipeline
        pass

    async def find_discord_member(self, bot, email: str):
        user_link = UserLink(self.config)
        await user_link.initialize()
        user_link.set_bot(bot)               
        return await user_link.get_member_by_email(email)

    def normalize_name(self, name):
        # Remove special characters and convert to lowercase
        return re.sub(r'[^\w\s]', '', name.lower())

    def name_similarity(self, name1, name2):
        # Split names into parts
        parts1 = set(name1.split())
        parts2 = set(name2.split())
        
        # Calculate Jaccard similarity
        intersection = len(parts1.intersection(parts2))
        union = len(parts1.union(parts2))
        
        return intersection / union if union > 0 else 0