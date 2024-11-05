import discord
from discord import app_commands
from discord.ext import commands
from core.cog import Cog
import asyncio

class DeleteConfirmView(discord.ui.View):
    def __init__(self, timeout=30):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()

class ServerManagementCog(Cog):
    def __init__(self, bot):
        super().__init__(bot, loggerTag='server_management')

    @app_commands.command(name="remove_all_channels", description="Remove all channels from the server")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_all_channels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        view = DeleteConfirmView()
        await interaction.followup.send(
            "⚠️ **WARNING**: This will delete **ALL** channels in the server. Are you absolutely sure?",
            view=view,
            ephemeral=True
        )

        # Wait for the button interaction
        timeout = await view.wait()
        
        if timeout or not view.value:
            await interaction.followup.send(
                "Operation cancelled: No confirmation received.",
                ephemeral=True
            )
            return

        # Create progress message
        progress = await interaction.followup.send(
            "Starting channel deletion process...",
            ephemeral=True
        )

        deleted_count = 0
        failed_count = 0
        error_messages = []

        # Delete all channels
        for channel in interaction.guild.channels:
            try:
                await channel.delete()
                deleted_count += 1
                if deleted_count % 5 == 0:  # Update progress every 5 channels
                    await progress.edit(content=f"Deleted {deleted_count} channels...")
            except discord.Forbidden:
                failed_count += 1
                error_messages.append(f"Failed to delete {channel.name}: Missing permissions")
            except discord.HTTPException:
                failed_count += 1
                error_messages.append(f"Failed to delete {channel.name}: HTTP error")

        # Create a new channel to inform about the deletion
        try:
            new_channel = await interaction.guild.create_text_channel('server-reset')
            await new_channel.send(
                f"All channels have been removed as requested by {interaction.user.mention}.\n"
                f"• Successfully deleted: {deleted_count} channels\n"
                f"• Failed to delete: {failed_count} channels"
            )
            
            if error_messages:
                error_log = "\n".join(error_messages[:10])  # Show first 10 errors
                if len(error_messages) > 10:
                    error_log += f"\n...and {len(error_messages) - 10} more errors"
                await interaction.user.send(f"Error log:\n```\n{error_log}\n```")

        except discord.Forbidden:
            await interaction.followup.send(
                "All channels were deleted, but I couldn't create a new channel to announce this. "
                "Make sure I have the necessary permissions.",
                ephemeral=True
            )

    @remove_all_channels.error
    async def remove_all_channels_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"An error occurred: {str(error)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(ServerManagementCog(bot))
    await bot.tree.sync()