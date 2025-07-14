import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from core.cog import Cog

class ServerManagementCog(Cog):
    def __init__(self, bot):
        super().__init__(bot, logger_tag='server_management')

    @app_commands.command(name="remove_all_channels", description="Remove all channels from the server")
    @commands.has_permissions(administrator=True)
    async def remove_all_channels(self, ctx):
        # Confirmation message
        confirmation = await ctx.send("⚠️ WARNING: This will delete ALL channels in the server. "
                                      "Are you absolutely sure? Type 'YES' to confirm.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.upper() == "YES"

        try:
            # Wait for confirmation
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await confirmation.edit(content="Command cancelled: You didn't confirm in time.")
            return
        else:
            # Delete all channels
            for channel in ctx.guild.channels:
                try:
                    await channel.delete()
                except discord.Forbidden:
                    await ctx.author.send(f"Failed to delete channel {channel.name}. Missing permissions.")
                except discord.HTTPException:
                    await ctx.author.send(f"Failed to delete channel {channel.name}. HTTP exception occurred.")

            # Create a new channel to inform about the deletion
            try:
                new_channel = await ctx.guild.create_text_channel('server-reset')
                await new_channel.send("All channels have been removed as requested by an administrator.")
            except discord.Forbidden:
                await ctx.author.send("All channels were deleted, but I couldn't create a new channel to announce this. "
                                      "Make sure I have the necessary permissions.")

async def setup(bot):
    await bot.add_cog(ServerManagementCog(bot))