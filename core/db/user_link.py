from core.db.DB import DB
import aiosqlite

class UserLink(DB):

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS member_gitlab_link
                (
                             discord_id INTEGER PRIMARY KEY, 
                             gitlab_email TEXT)
            ''')
            await db.commit()

    async def link_user(self, discord_id, gitlab_email):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO member_gitlab_link (discord_id, gitlab_email) VALUES (?, ?)', 
                             (discord_id, gitlab_email))
            await db.commit()

    async def get_gitlab_email(self, discord_id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT gitlab_email FROM member_gitlab_link WHERE discord_id = ?', (discord_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def get_discord_id(self, gitlab_email):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT discord_id FROM member_gitlab_link WHERE gitlab_email = ?', (gitlab_email,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None