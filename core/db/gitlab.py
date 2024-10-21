from db import DB
import aiosqlite

class Gitlab(DB):
    
    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS gitlab_config
                (
                             key TEXT PRIMARY KEY, 
                             value TEXT)
            ''')


    ### GITLAB CONFIG DATA FUNCTIONS
    async def set_gitlab_config(self, key, value):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO gitlab_config (key, value) VALUES (?, ?)', (key, value))
            await db.commit()

    async def get_gitlab_config(self, key):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT value FROM gitlab_config WHERE key = ?', (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None