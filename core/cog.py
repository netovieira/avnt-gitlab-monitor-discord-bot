from Config import Config
from core.logger import getLogger
from discord.ext import commands

class Cog(commands.Cog):
    def __init__(self, bot, logger_tag=None):
        self.bot = bot
        tag = 'cog'

        if logger_tag:
            tag += f':{logger_tag}'
        self.logger = getLogger(tag)

    @classmethod
    async def register(cls, bot):
        print(f"Registrando cog: {cls.__name__}")
        instance = cls(bot)
        print(f"Instância criada: {instance}")

        # Adiciona todos os comandos app_commands da classe à árvore
        for command in instance.__cog_app_commands__:
            bot.tree.add_command(command)

        print(f"Registrados {len(instance.__cog_app_commands__)} comandos no app_commands")