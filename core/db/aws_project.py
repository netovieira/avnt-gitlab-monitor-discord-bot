from db import DB
import aiosqlite

class AWSProject(DB):

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS aws_projects
                (
                             id INTEGER PRIMARY KEY,
                             aws_secret_key TEXT, 
                             aws_access_key TEXT, 
                             aws_region TEXT )
            ''')

    ### AWS PROJECTS DATA FUNCTIONS
    async def get_aws_projects(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT id, aws_access_key, aws_secret_key, aws_region FROM aws_projects') as cursor:
                return await cursor.fetchall()

    async def get_aws_project(self, id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT id, aws_access_key, aws_secret_key, aws_region FROM aws_projects WHERE id = ?', (id,)) as cursor:
                row = await cursor.fetchone()
                return row if row else None

    async def set_aws_project(self, project_id, aws_access_key, aws_secret_key, aws_region):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO projects (id, aws_access_key, aws_secret_key, aws_region) VALUES (?, ?, ?, ?)', 
                             (project_id, aws_access_key, aws_secret_key, aws_region))
            await db.commit()

    async def remove_aws_project(self, project_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM aws_projects WHERE id = ?', (project_id,))
            await db.commit()