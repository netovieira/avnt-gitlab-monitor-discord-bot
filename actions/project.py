import re
import asyncio

from discord.ui import Button, View
from core.db.aws_project import AWSProject
from core.db.project import Project, projectFromCursor
from core.discord import Discord
from core.env import WEBHOOK_HOST
from core.logger import getLogger
from helpers.gitlab import GitlabClient
from notification_templates import get_notification_message
from user_link import UserLink

# Set up logging
logger = getLogger('discord-actions:project')
class ProjectActions:

    guild = None
    last_id:int = -1
    project_id:int = None
    gitlab_project = None
    db = None
    gl = None
    discord = None

    category_name = None
    notification_channel_name = None

    # CHANNELS
    dashboard_channel = None
    category_channel = None
    notification_channel = None
    war_room_channel = None
    code_review_channel = None

    project = None

    def __init__(self, guild):
        self.db = Project()
        self.guild = guild
        self.discord = Discord(guild)
    

    async def load(self, project_id, force=True):
        
        if self.gl is None:
            self.gl = await GitlabClient.create()
        
        if self.last_id == project_id and not force:
            return self

        self.project_id = project_id
    
        gitlab_project_data = self.gl.instance.projects.get(project_id)
        if not gitlab_project_data:
            raise Exception(f"Project with ID {project_id} not found.")

        # Set Project and Discord properties  
        self.gitlab_project = gitlab_project_data

        group_name = gitlab_project_data.namespace['name'] if gitlab_project_data.namespace['kind'] == 'group' else "OTHER"
        project_url = gitlab_project_data.web_url
        
        if not self.category_name:
            self.category_name = group_name.upper()
        
        self.category_channel = await self.discord.addCategory(self.category_name)

        _ = await self.db.get_project(project_id)

        if not self.notification_channel_name:
            self.notification_channel_name = _[1] if _ else gitlab_project_data.path
        
        self.notification_channel = await self.discord.addTextChannel(self.notification_channel_name, self.category_name)
        self.war_room_channel = await self.discord.addVoiceChannel("WAR ROOM", self.category_name)
        self.code_review_channel = await self.discord.addVoiceChannel("CODE REVIEW", self.category_name)

        if _ is None:
            _ = [
                gitlab_project_data.id,
                None,
                self.notification_channel.id,
                self.category_channel.id,
                gitlab_project_data.path,
                self.category_name,
                group_name,
                project_url
            ]

        self.project = projectFromCursor(_)
        self.last_id = project_id

        return self
 
    async def setupDiscord(self):
        logger.info(f"--------------------------------------------------- setupDiscord ---------------------------------------------------")
        if self.category_channel is None:
            self.category_channel = await self.discord.addCategory(self.category_name)
            await self.discord.addVoiceChannel("WAR ROOM", self.category_name)
            await self.discord.addVoiceChannel("CODE REVIEW", self.category_name)

        if not self.notification_channel:
            self.notification_channel = await self.discord.addTextChannel(self.notification_channel_name, self.category_name)

    async def updateConfig(self):
        logger.info(f"--------------------------------------------------- updateConfig ---------------------------------------------------")
        # Add project to configuration    
        await self.db.set_project(
            self.gitlab_project.id,
            self.notification_channel_name,
            self.category_name,
            self.notification_channel.id,
            self.category_channel.id,
            self.project.url
        )
        self.project = projectFromCursor( await self.db.get_project(self.gitlab_project.id) )

    async def setupGitlab(self):
        logger.info(f"--------------------------------------------------- setupGitlab ---------------------------------------------------")
        # Set up webhook for the project
        webhook_url = f"{WEBHOOK_HOST}/webhook/{self.gitlab_project.id}"
        logger.info(f"WEBHOOK_HOST: {WEBHOOK_HOST}")
        logger.info(f"webhook_url: {webhook_url}")

        try:
            # Verificar se já existe um webhook com a mesma URL
            existing_hooks = await asyncio.to_thread(self.gitlab_project.hooks.list)
            for hook in existing_hooks:
                if hook.url == webhook_url:
                    logger.info(f"Webhook already exists for URL: {webhook_url}")
                    return  # Sai da função se o webhook já existir

            self.gitlab_project.hooks.create({
                'url': webhook_url,
                'push_events': True,
                'pipeline_events': True,
                'merge_requests_events': True,
                'token': self.gl.token,
                'enable_ssl_verification': False
            })

            logger.info(f"Set up webhook for project {self.gitlab_project.name}")
        except Exception as e:
            logger.error(f"Failed to create webhook: {str(e)}")
            raise Exception(f"Failed to set up webhook (url: {webhook_url}): {str(e)}")

    async def add(self, project_id: int = None, project_name: str = None, project_group: str = None):
        logger.info('Add project command triggered')

        if project_name != None:
            self.notification_channel_name = project_name

        if project_group != None:
            self.category_name = project_group
        
        if project_id:
            await self.load(project_id)

        await self.setup()

    async def add_aws_environment(self, project_id, environment, aws_access_key, aws_secret_key, aws_region):
        aws_project_manager = AWSProject()
        await aws_project_manager.set_aws_project(project_id, environment, aws_access_key, aws_secret_key, aws_region)

        return True


    async def setup(self):
        if self.gitlab_project:
            await self.updateConfig()
            await self.setupDiscord()
            await self.setupGitlab()

            await self.updateProject()

    
    async def updateProject(self):
        logger.info(f'Update project command triggered for project ID: {self.gitlab_project.id}')

        await self.db.set_project(
            self.project.id,
            self.project.name,
            self.project.group_name,
            self.notification_channel.id,
            self.category_channel.id,
            self.project.url,
        )
        

    async def remove(self):
        logger.info(f'Remove project command triggered for project ID: {self.gitlab_project.id}')

        if self.gitlab_project and self.project:
            self.db.remove_project(self.gitlab_project.id)
            self.discord.removeChannel(self.project.channel_id)

        if self.discord.getCategoryChannelsCount(self.category.id, "text") == 0:
            self.discord.removeCategory(self.category.id)

        if self.project.thread_id:
            self.discord.archiveForumThread(self.project.thread_id)
            
        
        webhooks = self.gitlab_project.hooks.list()
        for hook in webhooks:
            if hook.url.endswith(f"/webhook/{self.gitlab_project.id}"):
                self.gitlab_project.hooks.delete(hook.id)
                logger.info(f"Removed webhook for project {self.gitlab_project.name}")
                break


    async def handle_webhook(self, bot, data, event_type, channel, category):
        if event_type == 'Merge Request Hook':
            await self.handle_merge_request(bot, data, channel)
        elif event_type == 'Push Hook':
            await self.handle_push(data)
        elif event_type == 'Issue Hook':
            await self.handle_issue(data)
        elif event_type == 'Pipeline Hook':
            await self.handle_pipeline(data)
        else:
            logger.warning(f"Unhandled event type: {event_type}")

    async def handle_merge_request(self, bot, data, channel):
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


        await channel.send(message)
        
        if mr_url:
            button = Button(label="Mais informações", url=mr_url)
            view = View()
            view.add_item(button)
            await channel.send(view=view)

    async def handle_push(self, data, channel):
        # Implementar lógica para lidar com eventos de push
        pass

    async def handle_issue(self, data, channel):
        # Implementar lógica para lidar com eventos de issue
        pass

    async def handle_pipeline(self, data, channel):
        # Implementar lógica para lidar com eventos de pipeline
        pass

    async def find_discord_member(self, bot, email: str):
        user_link = UserLink()
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