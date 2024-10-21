from db import DB
import aiosqlite

class Project(DB):

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS projects
                (
                             id INTEGER PRIMARY KEY, 
                             name TEXT, 
                             group_id TEXT, 
                             channel_id TEXT, 
                             thread_id TEXT )
            ''')

    ### PROJECT DATA FUNCTIONS
    async def get_projects(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT id, name, group_name, channel_name FROM projects') as cursor:
                return await cursor.fetchall()

    async def get_project(self, id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT id, name, group_name, channel_name FROM projects WHERE id = ?', (id,)) as cursor:
                row = await cursor.fetchone()
                return row if row else None

    async def set_project(self, project_id, project_name, project_group, channel_id, group_id, thread_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO projects (id, name, group_name, channel_id, group_id, thread_id) VALUES (?, ?, ?, ?, ?, ?)', 
                             (project_id, project_name, project_group, channel_id, group_id, thread_id))
            await db.commit()

    async def remove_project(self, project_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
            await db.commit()