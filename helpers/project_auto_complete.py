import discord

from discord import app_commands
from core.db.project import Project


async def project_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[int]]:
    p = Project()
    projects = await p.get_projects()
    return [
       app_commands.Choice(name=f"{name} ({group_name})", value=id)
       for id, thread_id, channel_id, group_id, name, group_name, *_ in projects
       if current.lower() in name.lower() or current.lower() in group_name.lower()
   ][:25]