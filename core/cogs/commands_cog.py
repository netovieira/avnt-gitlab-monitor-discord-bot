from discord import app_commands
from discord.ext.commands import Context

from core.cog import Cog


class CommandsCog(Cog):

    def __init__(self, bot, logger_tag=None):
        tag = 'commands'

        if logger_tag is None:
            logger_tag = self.__class__.__name__

        if logger_tag:
            tag += f':{logger_tag}'
            
        super().__init__(bot, logger_tag=tag)

    async def cog_check(self, ctx) -> bool:
        """Sobrecarregue esse metodo para validações personalizadas"""
        return True

    # async def cog_load(self):
    #     """Automaticamente adiciona todos os app_commands da cog ao tree"""
    #     for command in self.__cog_app_commands__:
    #         try:
    #             self.bot.tree.add_command(command)
    #         except Exception as e:
    #             self.logger.warning(f"Comando {command.name} já existe: {e}")
    #
    #     self.logger.info(f"Processados {len(self.__cog_app_commands__)} comandos app_commands")
    #
    # async def cog_unload(self):
    #     """Remove todos os app_commands da cog do tree quando descarrega"""
    #     for command in self.__cog_app_commands__:
    #         self.bot.tree.remove_command(command.name)
    #     self.logger.info(f"Removidos {len(self.__cog_app_commands__)} comandos app_commands do tree")