# This DiscordManager class provides methods for managing Discord channels, categories, and user roles. It includes functionality to:

# Get or create a channel for a specific repository
# Get or create a category for a project
# Remove a user from the server
# Get or create a role
# Assign a role to a user
# Remove a role from a user

# These methods will be useful for organizing channels based on GitLab projects and repositories, as well as managing user permissions within the Discord server.




import discord
from discord.ext import commands

class DiscordManager:
    def __init__(self, bot):
        self.bot = bot

    async def get_or_create_channel(self, project_id, repository_name):
        guild = self.bot.guilds[0]  # Assuming the bot is in only one server
        category = await self.get_or_create_category(guild, project_id)
        
        channel = discord.utils.get(category.channels, name=repository_name.lower())
        if not channel:
            channel = await category.create_text_channel(repository_name.lower())
        
        return channel

    async def get_or_create_category(self, guild, project_id):
        category_name = f"Project-{project_id}"
        category = discord.utils.get(guild.categories, name=category_name)
        
        if not category:
            category = await guild.create_category(category_name)
        
        return category

    async def remove_user_from_server(self, user):
        guild = self.bot.guilds[0]  # Assuming the bot is in only one server
        member = guild.get_member(user.id)
        if member:
            try:
                await guild.kick(member, reason="Removed from GitLab project")
                print(f"Kicked user {member.display_name} from the server")
            except discord.errors.Forbidden:
                print(f"Failed to kick user {member.display_name}: Insufficient permissions")
        else:
            print(f"User {user.display_name} not found in the server")

    async def get_or_create_role(self, guild, role_name):
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            role = await guild.create_role(name=role_name)
        return role

    async def assign_role_to_user(self, user, role_name):
        guild = self.bot.guilds[0]  # Assuming the bot is in only one server
        member = guild.get_member(user.id)
        if member:
            role = await self.get_or_create_role(guild, role_name)
            try:
                await member.add_roles(role)
                print(f"Assigned role {role_name} to user {member.display_name}")
            except discord.errors.Forbidden:
                print(f"Failed to assign role {role_name} to user {member.display_name}: Insufficient permissions")
        else:
            print(f"User {user.name} not found in the server")

    async def remove_role_from_user(self, user, role_name):
        guild = self.bot.guilds[0]  # Assuming the bot is in only one server
        member = guild.get_member(user.id)
        if member:
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role in member.roles:
                try:
                    await member.remove_roles(role)
                    print(f"Removed role {role_name} from user {member.display_name}")
                except discord.errors.Forbidden:
                    print(f"Failed to remove role {role_name} from user {member.display_name}: Insufficient permissions")
        else:
            print(f"User {user.name} not found in the server")