import discord
from discord.channel import ForumChannel, Thread
from core.logger import getLogger
from typing import Union, Optional, Tuple


class Discord:
    def __init__(self, guild):
        self.logger = getLogger()
        self.guild = guild

    async def addCategory(self, category_name: str) -> discord.CategoryChannel:
        """
        Adds a new category to the Discord server.

        Parameters:
            category_name (str): The name of the category to be created.

        Returns:
            discord.CategoryChannel: The created or existing category.
        """
        category = discord.utils.get(self.guild.categories, name=category_name)
        if not category:
            category = await self.guild.create_category(category_name)
            self.logger.info(f"Created new category: {category_name}")
        else:
            self.logger.info(f"Using existing category: {category_name}")
        return category

    async def addTextChannel(self, channel_name: str, category_name: str = None) -> discord.TextChannel:
        """
        Creates a new text channel in the Discord server.

        Parameters:
            channel_name (str): The name of the text channel to be created.
            category_name (str, optional): The name of the category where the channel will be created.

        Returns:
            discord.TextChannel: The created or existing text channel.
        """
        category = None
        if category_name:
            category = await self.getCategory(category_name)
        
        if category is None:
            category = self.guild

        text_channel = discord.utils.get(self.guild.text_channels, name=channel_name)
        if not text_channel:
            text_channel = await category.create_text_channel(channel_name)
            self.logger.info(f"Created new text channel: {channel_name}")
        else:
            self.logger.info(f"Text channel '{channel_name}' already exists")

        return text_channel

    async def addForumChannel(self, channel_name: str, category_name: str = None, topic: str = None) -> ForumChannel:
        """
        Creates a new forum channel in the Discord server.

        Parameters:
            channel_name (str): The name of the forum channel to be created.
            category_name (str, optional): The name of the category where the channel will be created.
            topic (str, optional): The topic/description for the forum channel.

        Returns:
            ForumChannel: The created or existing forum channel.
        """
        category = None
        if category_name:
            category = await self.getCategory(category_name)
        
        if category is None:
            category = self.guild

        forum_channel = discord.utils.get(self.guild.forums, name=channel_name)
        if not forum_channel:
            forum_channel = await category.create_forum(
                name=channel_name,
                topic=topic,
                reason=f"Created forum channel: {channel_name}"
            )
            self.logger.info(f"Created new forum channel: {channel_name}")
        else:
            self.logger.info(f"Forum channel '{channel_name}' already exists")
            if topic and forum_channel.topic != topic:
                await forum_channel.edit(topic=topic)
                self.logger.info(f"Updated forum channel topic: {channel_name}")

        return forum_channel

    async def addVoiceChannel(self, channel_name: str, category_name: str = None) -> discord.VoiceChannel:
        """
        Creates a new voice channel in the Discord server.

        Parameters:
            channel_name (str): The name of the voice channel to be created.
            category_name (str, optional): The name of the category where the channel will be created.

        Returns:
            discord.VoiceChannel: The created or existing voice channel.
        """
        category = None
        if category_name:
            category = await self.getCategory(category_name)

        if category is None:
            category = self.guild

        voice_channel = discord.utils.get(self.guild.voice_channels, name=channel_name)
        if not voice_channel:
            voice_channel = await category.create_voice_channel(channel_name)
            self.logger.info(f"Created new voice channel: {channel_name}")
        else:
            self.logger.info(f"Voice channel '{channel_name}' already exists")
        
        return voice_channel

    async def getChannel(
        self, 
        channel_identifier: Union[str, int], 
        category: discord.CategoryChannel = None
    ) -> Optional[Union[discord.TextChannel, discord.VoiceChannel, ForumChannel]]:
        """
        Retrieves a channel from the Discord server.

        Parameters:
            channel_identifier (Union[str, int]): The name or ID of the channel to be retrieved.
            category (discord.CategoryChannel, optional): The category where the channel is located.

        Returns:
            Optional[Union[discord.TextChannel, discord.VoiceChannel, ForumChannel]]: The retrieved channel if found.
        """
        if isinstance(channel_identifier, int):
            # Search by ID
            channel = self.guild.get_channel(channel_identifier)
            if channel and category:
                return channel if channel.category_id == category.id else None
            return channel
        else:
            # Search by name
            if category:
                return discord.utils.get(category.channels, name=channel_identifier)
            
            # Search in all channel types
            channel = discord.utils.get(self.guild.text_channels, name=channel_identifier)
            if channel:
                return channel
            
            channel = discord.utils.get(self.guild.voice_channels, name=channel_identifier)
            if channel:
                return channel
            
            channel = discord.utils.get(self.guild.forums, name=channel_identifier)
            return channel

    async def getCategory(self, category_identifier: Union[str, int]) -> Optional[discord.CategoryChannel]:
        """
        Retrieves a category from the Discord server.

        Parameters:
            category_identifier (Union[str, int]): The name or ID of the category to be retrieved.

        Returns:
            Optional[discord.CategoryChannel]: The retrieved category if found.
        """
        if isinstance(category_identifier, int):
            return self.guild.get_channel(category_identifier)
        return discord.utils.get(self.guild.categories, name=category_identifier)

    async def removeChannel(
        self, 
        channel_identifier: Union[str, int], 
        reason: str = None,
        delete_threads: bool = True
    ) -> bool:
        """
        Removes a channel from the Discord server.

        Parameters:
            channel_identifier (Union[str, int]): The name or ID of the channel to be removed.
            reason (str, optional): The reason for removing the channel.
            delete_threads (bool): Whether to delete forum threads when removing a forum channel.

        Returns:
            bool: True if the channel was removed successfully, False otherwise.
        """
        try:
            channel = await self.getChannel(channel_identifier)
            if channel:
                # Handle forum channels specially
                if isinstance(channel, ForumChannel) and delete_threads:
                    # Delete all threads in the forum
                    async for thread in channel.archived_threads():
                        await thread.delete(reason=reason)
                    
                    # Delete active threads
                    for thread in channel.threads:
                        await thread.delete(reason=reason)

                await channel.delete(reason=reason)
                self.logger.info(f"Removed channel: {channel.name} (ID: {channel.id})")
                return True
            else:
                self.logger.warning(f"Channel not found: {channel_identifier}")
                return False
        except discord.Forbidden:
            self.logger.error(f"Insufficient permissions to remove channel: {channel_identifier}")
            return False
        except Exception as e:
            self.logger.error(f"Error removing channel {channel_identifier}: {str(e)}")
            return False

    async def removeCategory(self, category_identifier: Union[str, int], reason: str = None) -> bool:
        """
        Removes a category and all its channels from the Discord server.

        Parameters:
            category_identifier (Union[str, int]): The name or ID of the category to be removed.
            reason (str, optional): The reason for removing the category.

        Returns:
            bool: True if the category was removed successfully, False otherwise.
        """
        try:
            category = await self.getCategory(category_identifier)
            if category:
                # Remove all channels in the category
                for channel in category.channels:
                    # Handle forum channels specially
                    if isinstance(channel, ForumChannel):
                        # Delete all threads in the forum
                        async for thread in channel.archived_threads():
                            await thread.delete(reason=reason)
                        
                        # Delete active threads
                        for thread in channel.threads:
                            await thread.delete(reason=reason)

                    await channel.delete(reason=reason)
                    self.logger.info(f"Removed channel: {channel.name} (ID: {channel.id})")

                # Remove the category itself
                await category.delete(reason=reason)
                self.logger.info(f"Removed category: {category.name} (ID: {category.id})")
                return True
            else:
                self.logger.warning(f"Category not found: {category_identifier}")
                return False
        except discord.Forbidden:
            self.logger.error(f"Insufficient permissions to remove category: {category_identifier}")
            return False
        except Exception as e:
            self.logger.error(f"Error removing category {category_identifier}: {str(e)}")
            return False

    async def getCategoryChannelsCount(
        self, 
        category_identifier: Union[str, int], 
        channel_type: str = 'all'
    ) -> dict:
        """
        Gets the count of channels in a category.

        Parameters:
            category_identifier (Union[str, int]): The name or ID of the category
            channel_type (str): Type of channels to count ('all', 'text', 'voice', 'forum')

        Returns:
            dict: Dictionary with counts of different channel types
            {
                'total': int,
                'text': int,
                'voice': int,
                'forum': int
            }
        """
        try:
            category = await self.getCategory(category_identifier)
            if not category:
                self.logger.warning(f"Category not found: {category_identifier}")
                return {
                    'total': 0,
                    'text': 0,
                    'voice': 0,
                    'forum': 0
                }

            counts = {
                'total': len(category.channels),
                'text': len([c for c in category.channels if isinstance(c, discord.TextChannel)]),
                'voice': len([c for c in category.channels if isinstance(c, discord.VoiceChannel)]),
                'forum': len([c for c in category.channels if isinstance(c, ForumChannel)])
            }

            if channel_type.lower() != 'all':
                return {channel_type.lower(): counts.get(channel_type.lower(), 0)}
            
            return counts

        except Exception as e:
            self.logger.error(f"Error counting channels in category {category_identifier}: {str(e)}")
            return {
                'total': 0,
                'text': 0,
                'voice': 0,
                'forum': 0
            }

    async def getForumThread(self, thread_id: int) -> Optional[Thread]:
        """
        Gets a forum thread by its ID.

        Parameters:
            thread_id (int): The ID of the thread to find

        Returns:
            Optional[Thread]: The thread if found, None otherwise
        """
        try:
            thread = self.guild.get_thread(thread_id)
            if not thread:
                # Try fetching archived threads from all forum channels
                for channel in self.guild.forums:
                    async for archived_thread in channel.archived_threads():
                        if archived_thread.id == thread_id:
                            return archived_thread
            return thread
        except Exception as e:
            self.logger.error(f"Error getting thread {thread_id}: {str(e)}")
            return None

    async def removeForumThread(self, thread_id: int, reason: str = None) -> Tuple[bool, str]:
        """
        Removes a thread from a forum channel.

        Parameters:
            thread_id (int): The ID of the thread to remove
            reason (str, optional): The reason for removing the thread

        Returns:
            Tuple[bool, str]: (Success status, Message)
        """
        try:
            thread = await self.getForumThread(thread_id)
            
            if not thread:
                msg = f"Thread with ID {thread_id} not found"
                self.logger.warning(msg)
                return False, msg
            
            if not isinstance(thread.parent, ForumChannel):
                msg = f"Channel with ID {thread.parent.id} is not a forum channel"
                self.logger.warning(msg)
                return False, msg

            # Store info for logging
            thread_name = thread.name
            forum_name = thread.parent.name
            
            # Delete the thread
            await thread.delete(reason=reason)
            
            msg = f"Successfully removed thread '{thread_name}' from forum '{forum_name}'"
            self.logger.info(msg)
            return True, msg

        except discord.Forbidden:
            msg = f"Insufficient permissions to remove thread {thread_id}"
            self.logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error removing thread {thread_id}: {str(e)}"
            self.logger.error(msg)
            return False, msg

    async def getForumThreads(self, forum_identifier: Union[str, int], include_archived: bool = False) -> list[Thread]:
        """
        Gets all threads from a forum channel.

        Parameters:
            forum_identifier (Union[str, int]): The name or ID of the forum channel
            include_archived (bool): Whether to include archived threads

        Returns:
            list[Thread]: List of threads in the forum
        """
        try:
            channel = await self.getChannel(forum_identifier)
            
            if not channel or not isinstance(channel, ForumChannel):
                self.logger.warning(f"Forum channel not found or not a forum: {forum_identifier}")
                return []

            threads = list(channel.threads)
            
            if include_archived:
                async for archived_thread in channel.archived_threads():
                    threads.append(archived_thread)
            
            return threads

        except Exception as e:
            self.logger.error(f"Error getting threads from forum {forum_identifier}: {str(e)}")
            return []

    async def archiveForumThread(self, thread_id: int, archive: bool = True, reason: str = None) -> Tuple[bool, str]:
        """
        Archives or unarchives a forum thread.

        Parameters:
            thread_id (int): The ID of the thread to archive/unarchive
            archive (bool): True to archive, False to unarchive
            reason (str, optional): The reason for the action

        Returns:
            Tuple[bool, str]: (Success status, Message)
        """
        try:
            thread = await self.getForumThread(thread_id)
            
            if not thread:
                msg = f"Thread with ID {thread_id} not found"
                self.logger.warning(msg)
                return False, msg

            await thread.edit(archived=archive, reason=reason)
            
            action = "archived" if archive else "unarchived"
            msg = f"Successfully {action} thread '{thread.name}'"
            self.logger.info(msg)
            return True, msg

        except discord.Forbidden:
            msg = f"Insufficient permissions to modify thread {thread_id}"
            self.logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error modifying thread {thread_id}: {str(e)}"
            self.logger.error(msg)
            return False, msg