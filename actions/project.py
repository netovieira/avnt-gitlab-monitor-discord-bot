from config import Config
from core.discord import Discord
from core.env import WEBHOOK_HOST
from core.logger import getLogger
from helpers.gitlab import GitlabClient

# Set up logging
logger = getLogger('discord-actions:project')


class Project:

    ctx = None;
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

    def __init__(self, ctx):
        self.config = Config()
        self.ctx = ctx;
        self.discord = Discord(ctx);
    

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
        
        self.category_name = (self.project.namespace['name'] if self.project.namespace['kind'] == 'group' else "OTHER").upper()
        self.notification_channel_name = f"{self.project.name.lower().replace(' ', '-')}"
        
        self.category = self.discord.getCategory(self.category_name);
        self.notification_channel = self.discord.getChannel(self.notification_channel_name);
        self.war_room_channel = self.discord.getChannel("WAR ROOM", self.category);
        self.code_review_channel = self.discord.getChannel("CODE REVIEW", self.category);
        self.projectSettings = self.config.get_project(project_id);

        return self;

    async def setupDiscord(self):
        if not self.category:
            self.category = await self.discord.addCategory(self.category_name)
            await self.discord.addVoiceChannel("WAR ROOM", self.category)
            await self.discord.addVoiceChannel("CODE REVIEW", self.category)

        if not self.notification_channel:
            self.notification_channel = await self.discord.addTextChannel(self.notification_channel_name, self.category_name)

    async def updateConfig(self):
        # Add project to configuration    
        if not self.projectSettings:
            await self.config.add_project(self.project.id, self.project.name, self.category_name, self.notification_channel_name);
            self.projectSettings = await self.config.get_project(project_id=self.project.id);

    async def setupGitlab(self):
        logger.info(f"--------------------------------------------------- setupGitlab ---------------------------------------------------")
        # Set up webhook for the project
        webhook_url = f"{WEBHOOK_HOST}/webhook/{self.project.id}"
        logger.info(f"WEBHOOK_HOST: {WEBHOOK_HOST}")
        logger.info(f"webhook_url: {webhook_url}")

        try:
            response = await self.project.hooks.create({
                'url': webhook_url,
                'push_events': True,
                'pipeline_events': True,
                'merge_requests_events': True,
                'token': self.gl.token
            })
            logger.info(f"response {response}")

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