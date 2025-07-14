import asyncio
import discord
from discord import AllowedMentions

from helpers.chunk import markdown_aware_chunk, smart_chunk


async def create_text_channel_options(guild):
    options = []
    for category in guild.categories:
        options.append(discord.SelectOption(
            label=category.name,
            value=f"category_{category.id}",
            description="Selecionar todos os canais desta categoria"
        ))
        for channel in category.text_channels:
            options.append(discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"Canal em {category.name}"
            ))
    return options


async def response_list(interaction: discord.Interaction, messages_list: list[str], cap: int = 2000, is_markdown: bool = False, error_message: str = "❌ Erro: Conteúdo de ajuda não disponível."):
    full_content = ''.join(messages_list)

    if is_markdown:
        chunked = markdown_aware_chunk(full_content, cap)
    else:
        chunked = smart_chunk(full_content, cap)

    if not chunked:
        await interaction.response.send_message( error_message, ephemeral=True )
        return

    first, *rest = chunked

    await interaction.response.send_message(
        first,
        ephemeral=True,
        allowed_mentions=AllowedMentions.none(),
    )

    for i, chunk in enumerate(rest):
        await interaction.followup.send(
            chunk,
            ephemeral=True,
            allowed_mentions=AllowedMentions.none(),
            wait=True
        )

        if i > 0 and i % 5 == 0:  # (anti-rate-limit)
            await asyncio.sleep(0.2)