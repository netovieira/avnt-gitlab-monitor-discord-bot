import aiosqlite
from gitlab import Gitlab
from discord import Client
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class UserLink:
    def __init__(self, config):
        self.db_path = 'user_links.db'
        self.config = config
        self.bot = None
        self.gitlab = None

    async def initialize(self):
        gitlab_url = await self.config.get_gitlab_config('url')
        gitlab_token = await self.config.get_gitlab_config('token')
        if gitlab_url and gitlab_token:
            self.gitlab = Gitlab(gitlab_url, private_token=gitlab_token)
        await self._init_db()

    async def _init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_links (
                    discord_id INTEGER PRIMARY KEY,
                    gitlab_email TEXT UNIQUE,
                    role TEXT
                )
            ''')
            await db.commit()

    def set_bot(self, bot):
        self.bot = bot

    async def sync_users(self):
        if not self.gitlab:
            print("GitLab configuration is not set up.")
            return
        
        projects = await self.config.get_projects()
        for project_id, project_name in projects:
            project = self.gitlab.projects.get(project_id)
            members = project.members.list(all=True)

            logger.info(f'Project {project_name} {len(members)} members')
            
            for member in members:
                user = self.gitlab.users.get(member.id)
                await self.link_user_by_email(user.email, member.access_level)

    async def link_user_by_email(self, gitlab_email, access_level):
        role = self._get_role_from_access_level(access_level)
        discord_user = await self._find_discord_user_by_email(gitlab_email)
        logger.info(f'Gitlab user {gitlab_email} to discord member: {discord_user.id} into role: {role}')
        
        if discord_user:
            await self._link_user(discord_user.id, gitlab_email, role)

    def _get_role_from_access_level(self, access_level):
        # Map GitLab access levels to roles (customize as needed)
        if access_level >= 40:
            return 'manager'
        elif access_level >= 30:
            return 'developer'
        else:
            return 'guest'

    async def _find_discord_user_by_email(self, email):
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue

                user = await self.bot.fetch_user(member.id)
                if user.email and user.email.lower() == email.lower():
                    return user
        return None

    async def _link_user(self, discord_id, gitlab_email, role):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO user_links (discord_id, gitlab_email, role) VALUES (?, ?, ?)',
                             (discord_id, gitlab_email, role))
            await db.commit()

    async def get_user_by_email(self, gitlab_email):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT discord_id, role FROM user_links WHERE gitlab_email = ?', (gitlab_email,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    discord_id, role = result
                    user = await self.bot.fetch_user(discord_id)
                    return user, role
        return None, None

    async def get_users_by_role(self, role):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT discord_id FROM user_links WHERE role = ?', (role,)) as cursor:
                results = await cursor.fetchall()
                users = []
                for row in results:
                    user = await self.bot.fetch_user(row[0])
                    users.append(user)
                return users

    async def get_mention_string(self, roles):
        mentions = []
        for role in roles:
            users = await self.get_users_by_role(role)
            mentions.extend([user.mention for user in users])
        return ' '.join(mentions)