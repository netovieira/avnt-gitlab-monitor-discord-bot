from core.cog import Cog


class CommandsCog(Cog):

    def __init__(self, bot, loggerTag=None):
        tag = 'commands'
        if loggerTag:
            tag += f':{loggerTag}'
            
        super().__init__(bot, loggerTag=tag)
