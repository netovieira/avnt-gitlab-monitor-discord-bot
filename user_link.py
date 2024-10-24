import aiosqlite
from core.db.user_link import UserLink as UserLinkDB

class UserLink:
    def __init__(self):
        self.db = UserLinkDB()

    def set_bot(self, bot):
        self.bot = bot

    async def get_member(self, discord_id):
        for guild in self.bot.guilds:
            member = guild.get_member(discord_id)
            if member:
                return member
        return None

    async def get_member_by_email(self, email):
        for guild in self.bot.guilds:
            member = guild.get_member(await self.db.get_discord_id(email))
            if member:
                return member
        return None