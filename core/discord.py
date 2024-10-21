import discord

from core.logger import getLogger

class Discord:

    guild = None;
    logger = None;

    def __init__(self, guild):
        self.logger = getLogger();
        self.guild = guild;

    """
    Adds a new category to the Discord server.

    Parameters:
    category_name (str): The name of the category to be created.

    Returns:
    discord.CategoryChannel: The created or existing category.
    """
    async def addCategory(self, category_name):
        category = discord.utils.get(self.guild.categories, name=category_name)
        if not category:
            category = await self.guild.create_category(category_name)
            self.logger.info(f"Created new category: {category_name}")
        else:
            self.logger.info(f"Using existing category: {category_name}")
        return category

    """
    Creates a new text channel in the Discord server.

    Parameters:
    channel_name (str): The name of the text channel to be created.
    category_name (str, optional): The name of the category where the text channel will be created.
        If not provided, the text channel will be created in the server's default category.

    Returns:
    discord.TextChannel: The created or existing text channel.
    """
    async def addTextChannel(self, channel_name, category_name=None):

        category = None;

        if not (category_name is None): 
            category = discord.utils.get(self.guild.categories, name=category_name)

        if category is None: 
            category = self.guild          

        text_channel = discord.utils.get(self.guild.channels, name=channel_name)
        if not text_channel:
            text_channel = await category.create_text_channel(channel_name)
            self.logger.info(f"Created new text channel: {channel_name}")
        else:
            self.logger.info(f"Text channel '{channel_name}' already exists")

        return text_channel

    """
    Creates a new voice channel in the Discord server.

    Parameters:
    channel_name (str): The name of the voice channel to be created.
    category_name (str, optional): The name of the category where the voice channel will be created.
        If not provided, the voice channel will be created in the server's default category.

    Returns:
    discord.VoiceChannel: The created or existing voice channel.
    """
    async def addVoiceChannel(self, channel_name, category_name=None):

        category = None;

        if category_name is not None: 
            category = discord.utils.get(self.guild.categories, name=category_name)

        if category is None: 
            category = self.guild          

        text_channel = discord.utils.get(category.channels, name=channel_name)
        if not text_channel:
            text_channel = await category.create_voice_channel(channel_name)
            self.logger.info(f"Created new voice channel: {channel_name}")
        else:
            self.logger.info(f"Voice channel '{channel_name}' already exists")

    """
    Retrieves a channel from the Discord server.

    Parameters:
    channel_name (str): The name of the channel to be retrieved.
    category (discord.CategoryChannel, optional): The category where the channel is located.
        If not provided, the function will search for the channel in all categories.

    Returns:
    discord.TextChannel or discord.VoiceChannel: The retrieved channel if found, otherwise None.
    """
    async def getChannel(self, channel_name, category=None):
        if category is None:
            return discord.utils.get(self.guild.channels, name=channel_name)
        return discord.utils.get(category.channels, name=channel_name)
    
    """
    Retrieves a category from the Discord server.

    Parameters:
    category_name (str): The name of the category to be retrieved.

    Returns:
    discord.CategoryChannel: The retrieved category if found, otherwise None.
    """
    async def getCategory(self, category_name):
        return discord.utils.get(self.guild.categories, name=category_name)
    

# remove category with yours channels from discord
async def removeCategory(self, category_name):
    category = discord.utils.get(self.guild.categories, name=category_name)
    if category:
        # remove the category channels
        for channel in category.channels:
            await channel.delete()

        await category.delete()

    return True
