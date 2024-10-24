from Config import Config
from core.logger import getLogger
from discord.ext import commands

class Cog(commands.Cog):
    def __init__(self, bot, loggerTag=None):
        self.bot = bot
        tag = 'cog';

        if loggerTag:
            tag += f':{loggerTag}'
        self.logger = getLogger(tag)