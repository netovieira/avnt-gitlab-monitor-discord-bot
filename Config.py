import aiosqlite

class Config:
    def __init__(self):
        self.db_path = 'bot.db'

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS gitlab_config
                (
                             key TEXT PRIMARY KEY, 
                             value TEXT)
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS projects
                (
                             id INTEGER PRIMARY KEY, 
                             name TEXT, 
                             group_id TEXT, 
                             channel_id TEXT, 
                             thread_id TEXT )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS aws_projects
                (
                             id INTEGER PRIMARY KEY,
                             aws_secret_key TEXT, 
                             aws_access_key TEXT, 
                             aws_region TEXT )
            ''')
            await db.commit()


    
