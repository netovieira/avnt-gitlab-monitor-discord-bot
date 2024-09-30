import aiosqlite
import json
import os

class Config:
    def __init__(self, filename='config.json', db_path='config.db'):
        self.filename = filename
        self.db_path = db_path

    async def _init_db(self):
        # Ensure that the database and tables are initialized
        async with aiosqlite.connect(self.db_path) as db:
            # Create tables for roles and notifications if they do not exist
            await db.execute('''
                CREATE TABLE IF NOT EXISTS role_config (
                    role TEXT PRIMARY KEY,
                    email TEXT
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS notification_config (
                    event_type TEXT,
                    role TEXT,
                    PRIMARY KEY (event_type, role)
                )
            ''')
            await db.commit()

    async def load_config(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        return {}

    async def save_config(self, config):
        with open(self.filename, 'w') as f:
            json.dump(config, f, indent=2)

    async def get_gitlab_config(self, key):
        config = await self.load_config()
        return config.get('gitlab', {}).get(key)

    async def set_gitlab_config(self, key, value):
        config = await self.load_config()
        if 'gitlab' not in config:
            config['gitlab'] = {}
        config['gitlab'][key] = value
        await self.save_config(config)

    async def add_project(self, project_id, project_name, group_name, channel_name):
        config = await self.load_config()
        if 'projects' not in config:
            config['projects'] = []
        config['projects'].append((project_id, project_name, group_name, channel_name))
        await self.save_config(config)

    async def remove_project(self, project_id):
        config = await self.load_config()
        if 'projects' in config:
            config['projects'] = [p for p in config['projects'] if p[0] != project_id]
            await self.save_config(config)

    async def get_project(self, project_id):
        config = await self.load_config()
        projects = config.get('projects', [])
        return next((p for p in projects if p[0] == project_id), None)

    async def get_projects(self):
        config = await self.load_config()
        return config.get('projects', [])

    async def add_role(self, role, email):
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO role_config (role, email) VALUES (?, ?)', (role, email))
            await db.commit()

    async def get_roles(self):
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT role, email FROM role_config') as cursor:
                return await cursor.fetchall()

    async def add_notification(self, event_type, role):
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO notification_config (event_type, role) VALUES (?, ?)', (event_type, role))
            await db.commit()

    async def get_notifications(self):
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT event_type, role FROM notification_config') as cursor:
                return await cursor.fetchall()
